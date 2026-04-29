#include "board_config.h"

int main(void) {
    board_init();
    imu_init();
    while (1) {
        app_tick();
    }
    return 0;
}
