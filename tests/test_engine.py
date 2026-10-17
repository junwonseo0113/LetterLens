from app.rules.engine import Confidence, Profile, Status, evaluate


def _by_program(results, name):
    return next(r for r in results if r.program == name)


def test_a_single_senior_low_income_high_savings():
    profile = Profile(
        age=74,
        has_medicare=True,
        ss_gross_monthly=1700,
        savings=40_000,
    )
    results = evaluate(profile)
    msp = _by_program(results, "QMB")
    extra_help = _by_program(results, "Extra Help")
    snap = _by_program(results, "SNAP")

    assert msp.status == Status.LIKELY
    assert extra_help.status == Status.LIKELY
    assert "QMB" in extra_help.rule_applied
    assert snap.status == Status.LIKELY


def test_b_qi_tier():
    profile = Profile(age=70, has_medicare=True, ss_gross_monthly=2200)
    results = evaluate(profile)
    msp = _by_program(results, "QI")
    extra_help = _by_program(results, "Extra Help")

    assert msp.status == Status.LIKELY
    assert extra_help.status == Status.LIKELY
    assert "QI" in extra_help.rule_applied


def test_c_medigap_deduction_pushes_to_qi():
    profile = Profile(
        age=70,
        has_medicare=True,
        ss_gross_monthly=2600,
        medigap_premium_monthly=200,
    )
    results = evaluate(profile)
    msp = _by_program(results, "QI")

    assert msp.status == Status.LIKELY
    assert msp.numbers_used["countable_income_monthly"] == 2380.0


def test_d_earned_and_unearned_income_qmb():
    profile = Profile(
        age=70,
        has_medicare=True,
        ss_gross_monthly=900,
        earned_income_monthly=1500,
    )
    results = evaluate(profile)
    msp = _by_program(results, "QMB")

    assert msp.status == Status.LIKELY
    assert msp.numbers_used["countable_income_monthly"] == 1597.5


def test_e_married_couple_uses_couple_limits():
    profile = Profile(
        age=72,
        married=True,
        has_medicare=True,
        ss_gross_monthly=1200,
        ss_gross_monthly_spouse=1200,
    )
    results = evaluate(profile)
    msp = _by_program(results, "QMB")

    # combined 2400 - 20 disregard = 2380, under couple QMB limit (2489)
    assert msp.status == Status.LIKELY
    assert msp.numbers_used["countable_income_monthly"] == 2380.0


def test_f_ssdi_disability_no_work_warning():
    profile = Profile(
        age=62,
        has_medicare=True,
        disability=True,
        ss_gross_monthly=1500,
        savings=2000,
    )
    results = evaluate(profile)
    msp_or_tier = next(r for r in results if r.program in ("QMB", "QI", "MSP"))
    snap = _by_program(results, "SNAP")

    assert msp_or_tier.status == Status.LIKELY
    assert snap.status == Status.LIKELY
    assert snap.warnings == []


def test_g_no_medicare_part_time_job_work_warning():
    profile = Profile(
        age=62,
        has_medicare=False,
        earned_income_monthly=1200,
    )
    results = evaluate(profile)
    msp = _by_program(results, "MSP")
    extra_help = _by_program(results, "Extra Help")
    snap = _by_program(results, "SNAP")

    assert msp.status == Status.NOT_NOW
    assert extra_help.status == Status.NOT_NOW
    assert snap.status == Status.LIKELY
    assert any("work requirement" in w.lower() for w in snap.warnings)


def test_h_bank_deposit_only_estimated_confidence():
    profile = Profile(
        age=75,
        has_medicare=True,
        bank_deposit_monthly=1500,
    )
    results = evaluate(profile)
    msp = _by_program(results, "QMB")

    assert msp.status == Status.LIKELY
    assert msp.confidence == Confidence.ESTIMATED


def test_i_already_on_medicaid_extra_help_already_enrolled():
    profile = Profile(
        age=70,
        has_medicare=True,
        on_medicaid=True,
        ss_gross_monthly=1200,
    )
    results = evaluate(profile)
    extra_help = _by_program(results, "Extra Help")
    snap = _by_program(results, "SNAP")

    assert extra_help.status == Status.ALREADY_ENROLLED
    assert snap is not None


def test_j_income_too_high_not_now_with_explanation():
    profile = Profile(age=70, has_medicare=True, ss_gross_monthly=3000)
    results = evaluate(profile)
    msp = _by_program(results, "MSP")
    extra_help = _by_program(results, "Extra Help")
    snap = _by_program(results, "SNAP")

    assert msp.status == Status.NOT_NOW
    assert "exceeds" in msp.rule_applied
    assert extra_help.status == Status.NOT_NOW
    assert snap.status == Status.NOT_NOW
