"""Diagnostic integrity and target alignment; no external code or web visits."""
import unittest

from scripts.compare_ml_review import align, compare, scores


class MLReviewTests(unittest.TestCase):
    def test_confusion_counts_and_undefined_precision(self):
        result = scores([True, True, False, False], [True, False, True, False])
        self.assertEqual([result[k] for k in ('tp', 'fp', 'fn', 'tn')], [1, 1, 1, 1])
        self.assertEqual(result['balanced_accuracy'], .5)
        self.assertIsNone(scores([True, False], [False, False])['precision'])

    def test_alignment_rejects_changed_text_duplicates_and_missing_predictions(self):
        row = {'id': 'a', 'sample_origin': 'observed', 'label': 'normal', 'evidence_text': 'plain text'}
        self.assertEqual(align([row], [row]), [row])
        for records, predictions in (([row], []), ([row, row], [row]),
                                     ([row], [row, row]), ([row], [{**row, 'evidence_text': 'changed'}])):
            with self.subTest(predictions=predictions), self.assertRaises(ValueError):
                align(records, predictions)

    def test_supplied_corpus_hashes_metrics_and_indirect_exclusion(self):
        result = compare()
        self.assertEqual(result['n'], 73)
        self.assertEqual(result['excluded_indirect'], 5)
        self.assertEqual(result['labels'], {'ad_suspected': 50, 'normal': 23})
        rf = result['supplied_prototypes_recounted']['rf_char_tfidf']
        self.assertEqual([rf[k] for k in ('tp', 'fp', 'fn', 'tn')], [33, 6, 17, 17])
        self.assertEqual(len(result['cases']), len({r['id'] for r in result['cases']}))


if __name__ == '__main__':
    unittest.main()
