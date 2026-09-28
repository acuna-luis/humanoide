#include "tts_abi.hpp"
#include <dlfcn.h>
#include <cassert>
#include <cstdio>
#include <string>
int main(int argc,char** argv) {
  using Goal=sys_task_msgs::action::Tts_Goal;
  using Fn=void(*)(Goal*);
  auto fn=reinterpret_cast<Fn>(dlsym(RTLD_DEFAULT,"voice_en_apply_test"));assert(fn);
  Goal g;assert(&g.text_f()==&g.text && &g.language_f()==&g.language && &g.file_path_f()==&g.file_path);g.type_f(1);g.text_f("任务失败");g.language_f("zh");g.speed_f(42);g.volume_f(77);
  fn(&g);assert(g.text_f()=="The task failed."&&g.language_f()=="en"&&g.speed_f()==42&&g.volume_f()==77);
  g.text_f("42");g.language_f("zh");fn(&g);assert(g.text_f()=="42"&&g.language_f()=="en");
  g.text_f("完全未知的新错误987");g.language_f("zh");fn(&g);assert(g.text_f()=="完全未知的新错误987"&&g.language_f()=="zh");
  g.type_f(0);g.file_path_f("/example/es.wav");g.language_f("zh");fn(&g);assert(g.file_path_f()=="/example/es.wav"&&g.language_f()=="zh");
  void* h=dlopen("/opt/walker/task_manager/lib/libtask_manager_lib.so",RTLD_NOW|RTLD_GLOBAL);
  if(!h){std::fprintf(stderr,"dlopen: %s\n",dlerror());return 2;}
  const char* sym="_ZN12task_manager9TtsClient7on_sendERN13sys_task_msgs6action8Tts_GoalE";
  void* original=dlsym(h,sym);void* interposed=dlsym(RTLD_DEFAULT,sym);assert(original&&interposed&&original!=interposed);
  auto table=reinterpret_cast<void**>(dlsym(h,"_ZTVN12task_manager9TtsClientE"));assert(table);
  // Exact v0.2.0 ELF relocation recorded at vtable+0x78.
  assert(table[15]==interposed);
  std::puts("NATIVE_ABI_AND_VTABLE_BINDING_PASS; GOALS_SENT=0; PLAYBACK=0");
}
