int main() {
	return 0;
}

#define CMD_EXIT 0
#define CMD_START_AUDIO_CALL 1
#define CMD_END_AUDIO_CALL 2
#define CMD_START_VIDEO_CALL 3
#define CMD_END_VIDEO_CALL 4
#define CALL_TYPE_NONE 0
#define CALL_TYPE_AUDIO 1
#define CALL_TYPE_VIDEO 2


extern void resource_manager() {
    int curr_cmd;
    int is_mic_on = 0;
    int is_camera_on = 0;
    int curr_call_type = CALL_TYPE_NONE;
    
    while (1) {
        curr_cmd = random_selector();
        if (curr_cmd == CMD_EXIT) {
            break;
        } else if (curr_cmd == CMD_START_VIDEO_CALL) {
            if (curr_call_type == CALL_TYPE_NONE) {
                is_mic_on = 1;
                is_camera_on = 1;
                curr_call_type = CALL_TYPE_VIDEO;
            }
        } else if (curr_cmd == CMD_END_VIDEO_CALL) {
            if (curr_call_type == CALL_TYPE_VIDEO) {
                is_mic_on = 0;
                is_camera_on = 0;
                curr_call_type = CALL_TYPE_NONE;
            }
        } else if (curr_cmd == CMD_START_AUDIO_CALL) {
            if (curr_call_type == CALL_TYPE_NONE) {
                is_mic_on = 1;
                curr_call_type = CALL_TYPE_AUDIO;
            }
        } else if (curr_cmd == CMD_END_AUDIO_CALL) {
            if (curr_call_type == CALL_TYPE_AUDIO) {
                is_mic_on = 0;
                curr_call_type = CALL_TYPE_NONE;
            }
        }
    }
}

extern int random_selector() {
    return 0;
}
