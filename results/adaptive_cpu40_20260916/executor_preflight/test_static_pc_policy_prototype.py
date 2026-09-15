import unittest
from static_pc_policy_prototype import StaticPcPolicy


class StaticPcPolicyTest(unittest.TestCase):
    def test_no_idle_publications_before_bootstrap(self):
        policy = StaticPcPolicy()
        for n in range(50):
            self.assertFalse(policy.observe(n * 100_000_000, 0).publish)

    def test_bootstrap_once_without_subscribers(self):
        policy = StaticPcPolicy()
        first = policy.observe(5_000_000_000, 0)
        self.assertTrue(first.bootstrap)
        policy.published(first)
        for n in range(51, 101):
            self.assertFalse(policy.observe(n * 100_000_000, 0).publish)

    def test_delayed_callback_does_not_miss_bootstrap(self):
        policy = StaticPcPolicy()
        policy.observe(4_900_000_000, 0)
        self.assertTrue(policy.observe(8_000_000_000, 0).bootstrap)

    def test_early_subscriber_does_not_consume_bootstrap(self):
        policy = StaticPcPolicy()
        early = policy.observe(200_000_000, 1)
        self.assertTrue(early.subscriber_change)
        self.assertFalse(early.bootstrap)
        policy.published(early)
        self.assertTrue(policy.observe(5_000_000_000, 1).bootstrap)

    def test_late_rviz_change_after_bootstrap(self):
        policy = StaticPcPolicy()
        policy.published(policy.observe(5_000_000_000, 0))
        late = policy.observe(60_000_000_000, 1)
        self.assertTrue(late.subscriber_change)
        policy.published(late)
        self.assertFalse(policy.observe(60_100_000_000, 1).publish)

    def test_all_nonzero_count_changes_match_legacy_intent(self):
        policy = StaticPcPolicy()
        for subscribers in (1, 2, 1, 3):
            decision = policy.observe(1_000_000_000, subscribers)
            self.assertTrue(decision.subscriber_change)
            policy.published(decision)
        self.assertFalse(policy.observe(1_100_000_000, 0).publish)
        self.assertTrue(policy.observe(1_200_000_000, 1).publish)

    def test_bootstrap_and_count_change_coalesce(self):
        policy = StaticPcPolicy()
        decision = policy.observe(5_000_000_000, 1)
        self.assertTrue(decision.bootstrap and decision.subscriber_change)
        policy.published(decision)
        self.assertFalse(policy.observe(5_100_000_000, 1).publish)

    def test_unacknowledged_publication_retries(self):
        policy = StaticPcPolicy()
        self.assertTrue(policy.observe(5_000_000_000, 1).publish)
        retry = policy.observe(5_100_000_000, 1)
        self.assertTrue(retry.bootstrap and retry.subscriber_change)
        policy.published(retry)
        self.assertFalse(policy.observe(5_200_000_000, 1).publish)

    def test_policy_is_per_instance_not_function_static(self):
        first, second = StaticPcPolicy(), StaticPcPolicy()
        first.published(first.observe(5_000_000_000, 1))
        self.assertTrue(second.observe(5_000_000_000, 1).publish)

    def test_invalid_input(self):
        policy = StaticPcPolicy()
        with self.assertRaises(ValueError):
            policy.observe(0, -1)
        with self.assertRaises(ValueError):
            policy.observe(-1, 0)


if __name__ == '__main__':
    unittest.main()
