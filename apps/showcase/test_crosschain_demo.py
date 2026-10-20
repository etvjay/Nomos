import unittest
from crosschain_demo import CrossChainDemo, run_demo


class CrossChainDemoTests(unittest.TestCase):
    def test_semi_autonomous_requires_approval_then_settles(self):
        d = CrossChainDemo()
        j = d.adjudicate("clause 4.2 satisfied", True)
        self.assertEqual(d.release("p1", 150, j)["status"], "AWAITING_HUMAN_APPROVAL")
        result = d.release("p2", 150, j, approval=True)
        self.assertEqual(result["status"], "DESTINATION_SETTLED_SIMULATED")
        self.assertEqual(result["destination_balance_readback"], 150)

    def test_autonomous_corridor_is_bounded(self):
        result = run_demo("autonomous")
        self.assertEqual(result["status"], "DESTINATION_SETTLED_SIMULATED")
        self.assertEqual(result["destination_lz_eid"], 40245)
        self.assertEqual(result["destination_jurisdiction"], "GB")

    def test_rejected_judgment_never_releases(self):
        d = CrossChainDemo()
        j = d.adjudicate("evidence missing", False)
        result = d.release("p3", 150, j, approval=True)
        self.assertEqual(result["status"], "DENIED_ADJUDICATION")
        self.assertEqual(d.origin_balance, 1000)
        self.assertEqual(d.escrow.received, {})

    def test_caps_and_replay(self):
        d = CrossChainDemo()
        j = d.adjudicate("accepted", True)
        self.assertEqual(d.release("p4", 151, j, approval=True)["status"], "DENIED_PER_ACTION")
        self.assertEqual(d.release("p5", 150, j, approval=True)["status"], "DESTINATION_SETTLED_SIMULATED")
        self.assertEqual(d.release("p5", 150, j, approval=True)["status"], "DENIED_REPLAY")


if __name__ == "__main__":
    unittest.main()
