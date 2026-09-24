import unittest
from mode_text import split_mode_value, combine_mode_value


class ModeTextTests(unittest.TestCase):
    def test_plain_and_sub(self):
        self.assertEqual(split_mode_value('FT8'), ('FT8', ''))
        self.assertEqual(split_mode_value('FT8 AS'), ('FT8', 'AS'))
        self.assertEqual(combine_mode_value('FT8', 'AS', True), 'FT8 AS')
        self.assertEqual(combine_mode_value('FT8', 'AS', False), 'FT8')

    def test_known_space_mode_is_not_split(self):
        self.assertEqual(split_mode_value('VARA HF'), ('VARA HF', ''))
        self.assertEqual(split_mode_value('VARA HF AS'), ('VARA HF', 'AS'))
        self.assertEqual(split_mode_value('VARA FM 1200 AS'), ('VARA FM 1200', 'AS'))

    def test_unknown_space_mode_is_preserved(self):
        self.assertEqual(split_mode_value('FUTURE MODE'), ('FUTURE MODE', ''))


if __name__ == '__main__':
    unittest.main()
