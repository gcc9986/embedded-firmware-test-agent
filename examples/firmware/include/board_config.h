#pragma once

#define BOARD_NAME "dev-board-a"
#define I2C1_SPEED_HZ 400000

void board_init(void);
void app_tick(void);
int imu_init(void);
int i2c_read(int addr, int reg, unsigned char *buf, int len);
#define ASSERT(x) do { if (!(x)) while (1) {} } while (0)
