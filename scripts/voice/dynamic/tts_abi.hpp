#pragma once
// v0.2.0 compatibility declaration from the installed Tts.action/Tts.cxx.
// Installed headers omit Tts.h. Accessors/constructor/destructor are the native library's.
// Native tests verify field addresses, size and the actual vtable interposition.
#include <cstdint>
#include <cstddef>
#include <string>
namespace sys_task_msgs { namespace action {
class Tts_Goal {
public:
 uint8_t type; bool is_break;
 std::string file_path,text,speaker;
 int32_t speed,volume,pitch;
 std::string language,format;
 bool need_save;
 Tts_Goal(); ~Tts_Goal();
 void type_f(uint8_t); uint8_t type_f() const; uint8_t& type_f();
 void text_f(const std::string&); const std::string& text_f() const; std::string& text_f();
 void language_f(const std::string&); const std::string& language_f() const; std::string& language_f();
 void file_path_f(const std::string&); const std::string& file_path_f() const; std::string& file_path_f();
 void speed_f(int32_t);int32_t speed_f() const;int32_t& speed_f();
 void volume_f(int32_t);int32_t volume_f() const;int32_t& volume_f();
};
static_assert(sizeof(Tts_Goal)==192);
static_assert(offsetof(Tts_Goal,text)==40 && offsetof(Tts_Goal,language)==120);
}}
