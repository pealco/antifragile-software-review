from scoreboard import config, launch


def test_plan_covers_every_arm_task_and_trial():
    tasks = [{"id": "a", "difficulty": "easy"}, {"id": "b", "difficulty": "hard"}]
    planned = launch.plan(tasks, ["routed", "fixed"], 3)
    assert len(planned) == 12
    assert {t["arm"] for t in planned} == {"routed", "fixed"}


def test_routed_arm_points_at_proxy():
    settings = config.load()
    env = launch.agent_env(settings, settings.arms["routed"], "routed-a-0")
    assert env["LLM_BASE_URL"] == settings.proxy_url
    assert env["ROUTER_POLICY"] == "balanced"


def test_fixed_arm_goes_direct():
    settings = config.load()
    env = launch.agent_env(settings, settings.arms["fixed"], "fixed-a-0")
    assert env["LLM_BASE_URL"] == settings.provider_url
    assert env["LLM_MODEL"] == "corvid-7"
