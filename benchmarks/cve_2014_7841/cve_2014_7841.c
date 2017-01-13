#include <stddef.h>

int main() {
	return 0;
}

typedef int sctp_af;

#define SCTP_PARAM_IPV4_ADDRESS 5
#define SCTP_PARAM_IPV6_ADDRESS 6
#define SCTP_PARAM_SET_PRIMARY 0xc004
#define AF_INET 2
#define AF_INET6 10

static sctp_af sctp_af_v4_specific;
static sctp_af sctp_af_v6_specific;

extern void cve_2014_7841(int param_type) {
    sctp_af *af;
    int family;
    sctp_af read;

    if (param_type == SCTP_PARAM_IPV6_ADDRESS ||
            param_type == SCTP_PARAM_IPV4_ADDRESS) {
            
        // inline of: af = sctp_get_af_specific(param_type2af(param_type));
        if (param_type == SCTP_PARAM_IPV4_ADDRESS) {
            family = AF_INET;
        } else if (param_type == SCTP_PARAM_IPV6_ADDRESS) {
            family = AF_INET6;
        } else {
            family = 0;
        }
        
        if (family == AF_INET) {
            af = &sctp_af_v4_specific;
        } else if (family == AF_INET6) {
            af = &sctp_af_v6_specific;
        } else {
            af = NULL;
        }
        // end inline
        
        read = *af;
            
    } else if (param_type == SCTP_PARAM_SET_PRIMARY) {
        // inline of: af = sctp_get_af_specific(param_type2af(param_type));
        if (param_type == SCTP_PARAM_IPV4_ADDRESS) {
            family = AF_INET;
        } else if (param_type == SCTP_PARAM_IPV6_ADDRESS) {
            family = AF_INET6;
        } else {
            family = 0;
        }
        
        if (family == AF_INET) {
            af = &sctp_af_v4_specific;
        } else if (family == AF_INET6) {
            af = &sctp_af_v6_specific;
        } else {
            af = NULL;
        }
        // end inline
            
        if (af != NULL) {
            read = *af;
        }
    }
}
