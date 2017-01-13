int main() {
	return 0;
}

extern int allocate_list_item() {
    return 0;
}

extern int random_selector() {
    return 0;
}

extern void build_lists() {
    int x = allocate_list_item();// node *x = (node*)malloc(sizeof(node));
    int y = allocate_list_item(); // node *y = (node*)malloc(sizeof(node));
    int z; // node* z;
    while (random_selector()) {
        z = allocate_list_item(); // z = (node*)malloc(sizeof(node));
        if (random_selector()) {
            *((int*)z) = x; // z->next = x;
            x = z;
        } else {
            *((int*)z) = y; // z->next = y;
            y = z;
        }
    }
  // return (x, y);
}
