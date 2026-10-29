#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for cross_reference.py, including an end-to-end run against a
realistic staff-survey CSV modeled on the Riverside Family Practice sample
(14 tools, mix of approved/unapproved/wrong-tier) to confirm the matcher
actually resolves real-world display names against the DB.

Run: python3 test_cross_reference.py
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

import cross_reference as cr

HERE = Path(__file__).parent


class TestFuzzyMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(HERE / "ai_tools_db.json", encoding="utf-8") as f:
            cls.tools = json.load(f)["tools"]

    def test_alias_exact_match_chatgpt(self):
        matches = cr.find_matches("ChatGPT", self.tools)
        self.assertTrue(matches)
        # Should resolve to one of the OpenAI ChatGPT tier entries
        self.assertTrue(all(t["vendor"] == "OpenAI" for _, t in matches[:4]))

    def test_tier_hint_narrows_chatgpt_to_free(self):
        matches = cr.find_matches("ChatGPT", self.tools, tier_hint="Free")
        best_score, best = matches[0]
        self.assertEqual(best["tier"], "Free")

    def test_tier_hint_narrows_chatgpt_to_enterprise(self):
        matches = cr.find_matches("ChatGPT", self.tools, tier_hint="Enterprise")
        best_score, best = matches[0]
        self.assertIn("Enterprise", best["tier"])

    def test_fuzzy_match_without_alias(self):
        # "Otter AI" (no dot, extra space) should still resolve to Otter.ai
        matches = cr.find_matches("Otter AI (free)", self.tools, cutoff=0.4)
        self.assertTrue(matches)
        self.assertEqual(matches[0][1]["vendor"], "Otter.ai")

    def test_zoom_ai_companion_alias(self):
        matches = cr.find_matches("Zoom AI Companion", self.tools)
        self.assertEqual(matches[0][1]["id"], "zoom-zoom-ai-companion-zoom-business-(ai-companion-add-on)")

    def test_unknown_tool_returns_no_match(self):
        matches = cr.find_matches("Totally Fictional Nonexistent AI Tool XYZ123", self.tools, cutoff=0.55)
        self.assertEqual(matches, [])

    def test_dragon_medical_alias(self):
        matches = cr.find_matches("Dragon Medical One", self.tools)
        self.assertEqual(matches[0][1]["vendor"], "Microsoft/Nuance")


class TestEndToEndRiversideStyleSurvey(unittest.TestCase):
    """
    Models a realistic staff-survey export, using the same 14 tools (by
    display name, as a non-technical staff member would type them) that
    appear in the Riverside Family Practice sample AI Data Exposure
    Register, to confirm the cross-reference script actually produces a
    usable matrix from messy real-world input.
    """

    SURVEY_ROWS = [
        {"tool_name": "ChatGPT", "tier": "Free"},
        {"tool_name": "ChatGPT Team", "tier": "Team"},
        {"tool_name": "Microsoft 365 Copilot", "tier": ""},
        {"tool_name": "Google Gemini (Workspace)", "tier": ""},
        {"tool_name": "Gemini app on my phone", "tier": ""},
        {"tool_name": "Otter.ai", "tier": "Free"},
        {"tool_name": "Grammarly", "tier": "Business"},
        {"tool_name": "Claude.ai", "tier": "Free"},
        {"tool_name": "Perplexity", "tier": "Free"},
        {"tool_name": "DeepL", "tier": "Free"},
        {"tool_name": "Fireflies.ai", "tier": "Free"},
        {"tool_name": "Dragon Medical One", "tier": ""},
        {"tool_name": "Canva", "tier": "Free"},
        {"tool_name": "Zoom AI Companion", "tier": ""},
    ]

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.input_path = Path(self.tmpdir.name) / "survey.csv"
        with open(self.input_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["tool_name", "tier"])
            w.writeheader()
            for row in self.SURVEY_ROWS:
                w.writerow(row)

        with open(HERE / "ai_tools_db.json", encoding="utf-8") as f:
            self.tools = json.load(f)["tools"]

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_all_fourteen_rows_processed(self):
        rows_out, unmatched = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        self.assertEqual(len(rows_out), 14)

    def test_most_tools_matched(self):
        rows_out, unmatched = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        matched = [r for r in rows_out if r["matched_db_entry"]]
        # "Gemini app on my phone" is a deliberately messy, non-aliased input;
        # everything else should resolve.
        self.assertGreaterEqual(len(matched), 12)

    def test_chatgpt_free_flagged_high_risk(self):
        rows_out, _ = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        row = next(r for r in rows_out if r["input_tool_name"] == "ChatGPT")
        self.assertIn("High", row["risk_note"])
        self.assertEqual(row["approved_for_phi"], "N")

    def test_m365_copilot_shows_conditional_baa(self):
        rows_out, _ = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        row = next(r for r in rows_out if r["input_tool_name"] == "Microsoft 365 Copilot")
        self.assertEqual(row["baa_available"], "conditional")

    def test_dragon_medical_one_approved(self):
        rows_out, _ = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        row = next(r for r in rows_out if r["input_tool_name"] == "Dragon Medical One")
        self.assertTrue(row["baa_available"] is True or row["baa_available"] == "True")

    def test_csv_output_written(self):
        out_path = Path(self.tmpdir.name) / "out.csv"
        rows_out, _ = cr.process_input(self.input_path, "tool_name", "tier", self.tools)
        fields = ["input_tool_name", "matched_db_entry", "vendor_tier", "trains_on_input",
                  "baa_available", "dpa_in_place", "approved_for_phi", "risk_note",
                  "match_confidence", "db_source_urls"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows_out:
                w.writerow(r)
        with open(out_path, newline="", encoding="utf-8") as f:
            read_back = list(csv.DictReader(f))
        self.assertEqual(len(read_back), 14)


class TestOAuthSummaryInputFormat(unittest.TestCase):
    """Confirms the script also works directly on gworkspace_oauth_enum.py's
    output format (column name app_name instead of tool_name)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.input_path = Path(self.tmpdir.name) / "oauth_summary.csv"
        with open(self.input_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["app_name", "client_id", "user_count", "overall_risk"])
            w.writeheader()
            w.writerow({"app_name": "ChatGPT", "client_id": "123.apps.googleusercontent.com",
                        "user_count": "6", "overall_risk": "HIGH"})
            w.writerow({"app_name": "Otter.ai", "client_id": "456.apps.googleusercontent.com",
                        "user_count": "2", "overall_risk": "HIGH"})

        with open(HERE / "ai_tools_db.json", encoding="utf-8") as f:
            self.tools = json.load(f)["tools"]

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_app_name_column_works(self):
        rows_out, unmatched = cr.process_input(self.input_path, "app_name", None, self.tools)
        self.assertEqual(len(rows_out), 2)
        self.assertEqual(unmatched, [])


class TestMissingColumnErrorsClearly(unittest.TestCase):
    def test_missing_name_column_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["wrong_column"])
                w.writeheader()
                w.writerow({"wrong_column": "ChatGPT"})
            with open(HERE / "ai_tools_db.json", encoding="utf-8") as f:
                tools = json.load(f)["tools"]
            with self.assertRaises(SystemExit):
                cr.process_input(p, "tool_name", None, tools)


if __name__ == "__main__":
    unittest.main(verbosity=2)
