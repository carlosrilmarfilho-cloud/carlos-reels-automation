from __future__ import annotations

import json
import unittest
from pathlib import Path

import analyze_video
import render


ROOT = Path(__file__).resolve().parents[1]


class EditorialRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = json.loads((ROOT / "viral_copy.json").read_text(encoding="utf-8"))

    def test_every_theme_has_large_unique_clean_bank(self):
        for theme, section in self.bank.items():
            with self.subTest(theme=theme):
                overlays = render.expand_variants(section, "overlays")
                captions = render.expand_variants(section, "captions")
                self.assertGreaterEqual(len(overlays), 200)
                self.assertGreaterEqual(len(captions), 90)
                self.assertEqual(len(overlays), len(set(overlays)))
                self.assertEqual(len(captions), len(set(captions)))
                self.assertTrue(all(16 <= len(value) <= 82 for value in overlays))
                self.assertTrue(all(20 <= len(value) <= 220 for value in captions))
                self.assertFalse(any(render.contains_explicit_terms(value) for value in overlays + captions))

    def test_used_copy_is_never_selected_again(self):
        overlays = render.expand_variants(self.bank["forro_antigo"], "overlays")
        used = set(overlays[:35])
        chosen, _ = render.choose_unused(overlays, used, "fixed-seed")
        self.assertNotIn(chosen, used)

    def test_context_classification(self):
        cases = {
            "A terapia que tu precisa é um forró assim": "forro_antigo",
            "Uns fazem terapia, outros aumentam o brega": "brega",
            "Se um dia forem dividir o Brasil, me deixa do lado que": "nordeste_identidade",
            "Brasileiro morando longe de casa na Irlanda": "brasileiro_exterior",
            "Só quem trabalha de madrugada entende": "trabalho_noturno",
            "Mais um dia morando na minha van": "vanlife",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(analyze_video.classify(text), expected)


class LayoutRulesTests(unittest.TestCase):
    def test_compact_overlay_stays_above_face(self):
        analysis = {
            "text_bbox_norm": {"x0": 0.12, "y0": 0.17, "x1": 0.87, "y1": 0.20},
            "face_boxes_norm": [
                {"x0": 0.14, "y0": 0.275, "x1": 0.86, "y1": 0.68, "sample_time": 8.0}
            ],
            "head_boxes_norm": [],
        }
        rect, faces = render.make_overlay(
            "A distância só confirma que o Nordeste continua morando na gente.",
            analysis,
            (2160, 3840),
            (1440, 2560),
        )
        normalized = render.normalized_rect(rect, 1440, 2560)
        self.assertLessEqual(normalized["y1"] - normalized["y0"], 0.145)
        self.assertTrue(faces)
        self.assertLessEqual(render.overlap_fraction(rect, faces[0]), 0.035)

    def test_render_preserves_full_frame(self):
        source = (ROOT / "render.py").read_text(encoding="utf-8")
        self.assertIn("force_original_aspect_ratio=decrease", source)
        self.assertNotIn("force_original_aspect_ratio=increase,crop", source)


if __name__ == "__main__":
    unittest.main()
