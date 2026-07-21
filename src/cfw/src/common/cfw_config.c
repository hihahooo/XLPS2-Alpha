/* XLPS2-Alpha CFW — runtime config accessors (values mirror cfw_config.h) */
#include "common/cfw_config.h"
#include <string.h>

const char* cfw_fw_version(void)    { return CFW_FW_VERSION; }
const char* cfw_smdl_version(void)  { return CFW_SMDL_VERSION; }
uint32_t    cfw_param_version(void) { return CFW_PARAM_VERSION; }

/* monotonic version compare: a > b  => positive */
int cfw_version_cmp(const char* a, const char* b)
{
    return strcmp(a, b); /* lexical; SSOT requires strict-greater on publish */
}
