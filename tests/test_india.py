from jobhunter.india.india_hunter import salary_decision


def test_no_salary_is_accepted():
    assert salary_decision("")[0] is True
    assert salary_decision(None)[0] is True


def test_inr_lpa_above_40_accepted_below_rejected():
    assert salary_decision("₹45 LPA")[0] is True
    assert salary_decision("INR 30 LPA")[0] is False
    assert salary_decision("", amount_max=4_500_000, currency="INR")[0] is True
    assert salary_decision("", amount_max=3_000_000, currency="INR")[0] is False


def test_other_currency_not_accepted():
    accept, reason = salary_decision("$90,000 per year")
    assert accept is False and "another currency" in reason


def test_same_job_from_two_sources_has_same_key():
    from jobhunter.india.india_hunter import job_key
    assert job_key("DevOps Engineer", "Barclays") == job_key("devops  engineer", "BARCLAYS ")
    assert job_key("DevOps Engineer", "Barclays") != job_key("DevOps Engineer", "Citi")
