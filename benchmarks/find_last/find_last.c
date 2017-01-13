#include <stddef.h>

int main() {
	return 0;
}

extern int* find_last(int *p, int c) {
    int *q = NULL;
    int x;
    for (x = *p; x != 0; ++p, x = *p) {
        if (x == c) {
            q = p;
        }
    }
    return q;
}
