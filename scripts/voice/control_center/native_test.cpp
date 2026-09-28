#include "tts_abi.hpp"
#include "catalog.hpp"
#include <cassert>
#include <cstdio>
#include <unistd.h>
using Goal=sys_task_msgs::action::Tts_Goal;
int main() {
 for(const auto& row:cc_catalog) {
  Goal original;original.type_f(1);original.text_f(row.first);
  original.speed_f(42);original.volume_f(77);original.is_break=true;original.need_save=true;
  Goal copy(original);Goal assigned;assigned=original;
  bool file=access((std::string(CC_AUDIO_ROOT)+"/"+row.second.first+".wav").c_str(),R_OK)==0;
  for(auto g:{&copy,&assigned}) {
   assert(g->speed_f()==42 && g->volume_f()==77 && g->is_break && g->need_save);
   assert(g->pitch==original.pitch && g->speaker==original.speaker && g->format==original.format);
   if(file){assert(g->type_f()==0);assert(g->file_path_f()==std::string(CC_AUDIO_ROOT)+"/"+row.second.first+".wav");}
   else {assert(g->type_f()==1);assert(g->text_f()==row.second.second);assert(g->language_f()=="en");}
  }
  assert(original.text_f()==row.first && original.type_f()==1);
 }
 Goal a;a.type_f(1);a.text_f("当前电池电量分别是67.5%，75%。");
 Goal b(a);assert(b.text_f()=="Battery levels are 67.5 percent and 75 percent." && b.language_f()=="en");
 for(auto text:{"未知故障", "当前电池电量分别是101%，75%。", "Current mode ready."}) {
  a.text_f(text);Goal c(a);assert(c.text_f()==text && c.language_f()==a.language_f());
 }
 a.type_f(0);a.file_path_f("/original.wav");a.text_f("正在关机");
 Goal c(a);assert(c.type_f()==0 && c.file_path_f()=="/original.wav" && c.language_f()==a.language_f());
 std::puts("PASS: 24 fixed, native copy/assignment, battery, unknown, FILE, metadata, input preservation; GOALS=0 PLAYBACK=0");
}
