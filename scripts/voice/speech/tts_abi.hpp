#pragma once
// Compatibility declaration for the measured v0.2.0 libsys_task_msgs.so ABI.
// The request and FastCDR types stay opaque: the native goal_f() accessor finds
// the goal after the complete request has been deserialized successfully.
#include <cstddef>
#include <cstdint>
#include <string>

namespace sys_task_msgs { namespace action {
class Tts_Goal {
public:
    uint8_t type;
    bool is_break;
    std::string file_path, text, speaker;
    int32_t speed, volume, pitch;
    std::string language, format;
    bool need_save;

    Tts_Goal();
    ~Tts_Goal();
    void type_f(uint8_t);
    uint8_t type_f() const;
    std::string& text_f();
    std::string& language_f();
    std::string& file_path_f();
};
static_assert(sizeof(Tts_Goal) == 192);
static_assert(offsetof(Tts_Goal, file_path) == 8);
static_assert(offsetof(Tts_Goal, text) == 40);
static_assert(offsetof(Tts_Goal, language) == 120);
}}

// Exported native C helpers used only by the standalone serialization test.
// Their argument layouts and the Request PubSubType call were checked in ELF.
// json_to_cdr returns an owned SerializedPayload_t* plus its capacity, NOT a
// byte buffer. cdr_to_json instead consumes payload.data and payload.length.
extern "C" void serialize_sys_task_msgs_action_Tts_SendGoal_Request_json_to_cdr(
    const char*, void**, uint32_t*);
extern "C" void deserialize_sys_task_msgs_action_Tts_SendGoal_Request_cdr_to_json(
    const void*, uint32_t, char**, size_t*);
extern "C" void delete_sys_task_msgs_action_Tts_SendGoal_Request_serialize_data(void*);
extern "C" void free_sys_task_msgs_action_Tts_SendGoal_Request_json_str(char*);
