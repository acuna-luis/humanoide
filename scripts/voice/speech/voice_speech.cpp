// VOICE-SPEECH-08: exact-catalog localization in the speech receiver only.
// Native deserialization always finishes first; UUID, action callbacks, motion,
// unknown utterances and FILE requests keep their original behavior.
#include "tts_abi.hpp"
#include "catalog.hpp"
#include <dlfcn.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <string>

using Goal = sys_task_msgs::action::Tts_Goal;

static bool enabled() {
    static const bool value = [] {
        char path[4096];
        const auto count = readlink("/proc/self/exe", path, sizeof(path)-1);
        if (count < 0 || count == static_cast<ssize_t>(sizeof(path)-1)) return false;
        path[count] = 0;
        const std::string full(path);
        const auto name = full.substr(full.find_last_of('/')+1);
        return name == "speech_service" || name == "voice_speech_native_test";
    }();
    return value;
}

static void* native(const char* name) {
    void* pointer = dlsym(RTLD_NEXT, name);
    if (!pointer) {
        std::fputs("[VOICE_SPEECH] incompatible native ABI\n", stderr);
        std::abort();
    }
    return pointer;
}

static void apply(Goal& goal) noexcept {
    if (goal.type_f() != 1) return;
    try {
        const auto found = speech_catalog.find(goal.text_f());
        if (found == speech_catalog.end()) return;
        std::string path = std::string(SPEECH_AUDIO_ROOT)+"/"+found->second.first+".wav";
        struct stat metadata {};
        if (stat(path.c_str(), &metadata) == 0 && S_ISREG(metadata.st_mode) && access(path.c_str(), R_OK) == 0) {
            // Allocate before changing any native field. The remaining swaps
            // and native scalar setter cannot allocate.
            goal.file_path_f().swap(path);
            goal.type_f(0);
            std::fputs("[VOICE_SPEECH] exact announcement -> Spanish FILE\n", stderr);
        } else {
            std::string text = found->second.second;
            std::string language = "en";
            goal.text_f().swap(text);
            goal.language_f().swap(language);
            std::fputs("[VOICE_SPEECH] Spanish file unavailable -> English TTS\n", stderr);
        }
    } catch (...) {
        std::fputs("[VOICE_SPEECH] localization failed; native announcement retained\n", stderr);
    }
}

extern "C" void speech_deserialize_request(void*, void*)
    asm("_ZN8eprosima7fastcdr11deserializeIN13sys_task_msgs6action20Tts_SendGoal_RequestEEEvRNS0_3CdrERT_");

extern "C" void speech_deserialize_request(void* cdr, void* request) {
    using Deserialize = void(*)(void*, void*);
    static const auto deserialize = reinterpret_cast<Deserialize>(native(
        "_ZN8eprosima7fastcdr11deserializeIN13sys_task_msgs6action20Tts_SendGoal_RequestEEEvRNS0_3CdrERT_"));
    deserialize(cdr, request); // Preserve native exceptions; never localize partial input.
    if (!enabled()) return;
    using GetGoal = Goal&(*)(void*);
    static const auto get_goal = reinterpret_cast<GetGoal>(native(
        "_ZN13sys_task_msgs6action20Tts_SendGoal_Request6goal_fEv"));
    apply(get_goal(request));
}
