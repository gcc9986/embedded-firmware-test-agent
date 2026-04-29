#include "board_config.h"

#define IMU_ADDR 0x68
#define REG_WHOAMI 0x75

int imu_init(void) {
    unsigned char id = 0;
    int ret = i2c_read(IMU_ADDR, REG_WHOAMI, &id, 1);
    ASSERT(ret == 0);
    return ret;
}
