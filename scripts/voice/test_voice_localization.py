import unittest
from localize_tts_text import localize

class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'zh':'任务失败','en':'The task failed.','kind':'fixed'},
                   {'zh':'{message}','en':'','kind':'dynamic'}]
    def test_error_preserves_meaning(self):
        self.assertEqual(localize('任务失败',self.rows),'The task failed.')
    def test_unmapped_chinese_is_not_disguised(self):
        with self.assertRaises(ValueError):localize('电机新错误',self.rows)
    def test_dynamic_value_not_variable_name(self):
        self.assertEqual(localize('42',self.rows),'42')
        self.assertEqual(localize('Motor fault 42',self.rows),'Motor fault 42')

if __name__=='__main__':unittest.main()
