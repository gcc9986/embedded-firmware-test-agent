from embedded_test_agent.rules import classify_failure, infer_risk_tags


def test_i2c_timeout_classified_as_peripheral():
    serial_log = """
    [00:00.302] i2c: I2C1 timeout while reading addr=0x68 reg=0x75 retry=3
    [00:00.311] ASSERT failed: imu_init at src/drivers/imu.c:128
    """
    changed_files = ["src/drivers/imu.c", "src/bsp/i2c_bus.c"]
    risk_tags = infer_risk_tags(changed_files, "")
    status, hypotheses = classify_failure(
        serial_log=serial_log,
        changed_files=changed_files,
        risk_tags=risk_tags,
    )
    assert status == "FAIL"
    assert hypotheses
    assert hypotheses[0].category == "PERIPHERAL_COMMUNICATION"
    assert hypotheses[0].confidence >= 0.86


def test_build_error_classified_as_config():
    build_log = 'src/drivers/imu.c:42:10: fatal error: imu_regsiters.h: No such file or directory'
    status, hypotheses = classify_failure(build_log=build_log, changed_files=["src/drivers/imu.c"])
    assert status == "FAIL"
    assert hypotheses[0].category == "BUILD_CONFIG_ERROR"
