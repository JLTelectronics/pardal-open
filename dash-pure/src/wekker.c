#include <fcntl.h>
#include <stdint.h>
#include <sys/time.h>
struct input_event { struct timeval time; uint16_t type; uint16_t code; int32_t value; };
#define EV_SYN 0x00
#define EV_KEY 0x01
#define SYN_REPORT 0
#define KEY_POWER 116
#define BTN_TOUCH 0x14a
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <poll.h>

static long now_ms(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000L + t.tv_nsec / 1000000L;
}

static int backlight(const char *f) {
    char b[16] = {0}; int fd = open(f, O_RDONLY); if (fd < 0) return -1;
    int n = read(fd, b, sizeof b - 1); close(fd); return n > 0 ? atoi(b) : -1;
}

static void press_power(const char *dev) {
    int fd = open(dev, O_WRONLY); if (fd < 0) return;
    struct input_event ev[4]; memset(ev, 0, sizeof ev);
    ev[0].type = EV_KEY; ev[0].code = KEY_POWER; ev[0].value = 1;
    ev[1].type = EV_SYN; ev[1].code = SYN_REPORT;
    ev[2].type = EV_KEY; ev[2].code = KEY_POWER; ev[2].value = 0;
    ev[3].type = EV_SYN; ev[3].code = SYN_REPORT;
    write(fd, ev, sizeof ev); close(fd);
}

int main(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1], "druk")) { press_power(argc > 2 ? argv[2] : "/dev/input/event1"); return 0; }
    const char *tdev = argc > 1 ? argv[1] : "/dev/input/event2";
    const char *kdev = argc > 2 ? argv[2] : "/dev/input/event1";
    const char *bl   = argc > 3 ? argv[3] : "/sys/class/leds/lcd-backlight/brightness";
    long off_since = -1, last_wake = 0;
    for (;;) {
        int fd = open(tdev, O_RDONLY);
        if (fd < 0) { sleep(2); continue; }
        struct input_event e;
        struct pollfd p = { .fd = fd, .events = POLLIN };
        for (;;) {
            int r = poll(&p, 1, 500);
            long t = now_ms();
            int b = backlight(bl);
            if (b != 0) off_since = -1;
            else if (off_since < 0) off_since = t;
            if (r < 0) break;
            if (r == 0) continue;
            if (read(fd, &e, sizeof e) != sizeof e) break;
            if (b != 0) continue;
            if (e.type != EV_KEY || e.code != BTN_TOUCH || e.value != 1) continue;
            if (t - off_since < 3000) continue;
            if (t - last_wake < 2000) continue;
            press_power(kdev); last_wake = t; off_since = -1;
            FILE *l = fopen("/tmp/wekker.log", "a");
            if (l) { fprintf(l, "%ld wakker door aanraking\n", (long)time(0)); fclose(l); }
        }
        close(fd); sleep(1);
    }
}
