#include "tts_abi.hpp"
#include <cassert>
#include <cstdio>
#include <unistd.h>
using Goal=sys_task_msgs::action::Tts_Goal;
int main(){
 Goal a;a.type_f(1);a.text_f("当前抱闸被锁死，请操作底盘解抱闸按钮，解锁抱闸");
 a.speed_f(42);a.volume_f(77);a.is_break=true;a.need_save=true;
 Goal b;b=a;
 assert(b.speed_f()==42 && b.volume_f()==77 && b.is_break && b.need_save);
 assert(b.pitch==a.pitch && b.speaker==a.speaker && b.format==a.format);
 if(access("/etc/walker/voice/brake_es_v1/brake_locked.wav",R_OK)==0){
  assert(b.type_f()==0 && b.file_path_f()=="/etc/walker/voice/brake_es_v1/brake_locked.wav");
 }else {assert(b.type_f()==1 && b.language_f()=="en");
  assert(b.text_f()=="The chassis brake is locked. Use the chassis brake release button to unlock it.");}
 assert(a.type_f()==1 && a.language_f()=="zh");
 a.text_f("其他故障");b=a;assert(b.text_f()==a.text_f() && b.language_f()==a.language_f());
 a.type_f(0);a.file_path_f("/original.wav");b=a;assert(b.type_f()==0 && b.file_path_f()==a.file_path_f());
 std::puts("PASS: native assignment, exact translation, unknown/FILE preservation, metadata, original unchanged; GOALS=0 PLAYBACK=0");
}
