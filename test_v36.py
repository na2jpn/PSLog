import unittest
from contest_ui import uses_iburi_hidaka_joint

class V36ContestTargetUiTests(unittest.TestCase):
    def test_iburi_joint_option_is_contest_specific(self):
        self.assertTrue(uses_iburi_hidaka_joint({'id':'iburi_hidaka'}))
        self.assertFalse(uses_iburi_hidaka_joint({'id':'gigahertz'}))
        self.assertFalse(uses_iburi_hidaka_joint(None))

if __name__=='__main__':
    unittest.main()
