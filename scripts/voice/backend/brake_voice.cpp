// VOICE-BRAKE-07: translate one exact utterance in backend_service_vision only.
#include "tts_abi.hpp"
#include <dlfcn.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <string>
using Goal=sys_task_msgs::action::Tts_Goal;
static bool enabled() {
 static bool value=[] {char path[4096];auto n=readlink("/proc/self/exe",path,sizeof(path)-1);
  if(n<0)return false;path[n]=0;std::string p(path);auto name=p.substr(p.find_last_of('/')+1);
  return name=="backend_service_vision" || name=="brake_voice_native_test";}();
 return value;
}
extern "C" Goal* assign(Goal*,const Goal*) asm("_ZN13sys_task_msgs6action8Tts_GoalaSERKS1_");
extern "C" Goal* assign(Goal* dst,const Goal* src) {
 static auto fn=[] {auto p=dlsym(RTLD_NEXT,"_ZN13sys_task_msgs6action8Tts_GoalaSERKS1_");
  if(!p){std::fputs("[VOICE_BRAKE] incompatible native ABI\n",stderr);std::abort();}
  return reinterpret_cast<Goal*(*)(Goal*,const Goal*)>(p);}();
 Goal* result=fn(dst,src);
 if(!enabled() || dst->type_f()!=1 || dst->text_f()!="当前抱闸被锁死，请操作底盘解抱闸按钮，解锁抱闸")return result;
 try {
  std::string path="/etc/walker/voice/brake_es_v1/brake_locked.wav";
  if(access(path.c_str(),R_OK)==0){dst->file_path_f().swap(path);dst->type_f(0);
   std::fputs("[VOICE_BRAKE] exact announcement -> Spanish FILE\n",stderr);}
  else {std::string text="The chassis brake is locked. Use the chassis brake release button to unlock it.",language="en";
   dst->text_f().swap(text);dst->language_f().swap(language);
   std::fputs("[VOICE_BRAKE] file unavailable -> English TTS\n",stderr);}
 }catch(...){std::fputs("[VOICE_BRAKE] localization failed; native goal retained\n",stderr);}
 return result;
}
