// VOICE-BOOT-05: only copies of Tts_Goal in Control Center are localized.
// The native copy executes first. No task, state-machine, or motion APIs.
#include "tts_abi.hpp"
#include "catalog.hpp"
#include <dlfcn.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <regex>
#include <string>
using Goal=sys_task_msgs::action::Tts_Goal;
static bool enabled() {
 static bool value=[] { char path[4096]; auto n=readlink("/proc/self/exe",path,sizeof(path)-1);
  if(n<0)return false; path[n]=0;std::string p(path);
  auto name=p.substr(p.find_last_of('/')+1);
  return name=="control_center" || name=="voice_cc_native_test"; }();
 return value;
}
static void apply(Goal& g) noexcept {
 if(!enabled() || g.type_f()!=1)return;
 try {
  auto found=cc_catalog.find(g.text_f());
  if(found!=cc_catalog.end()) {
   std::string path=std::string(CC_AUDIO_ROOT)+"/"+found->second.first+".wav";
   if(access(path.c_str(),R_OK)==0) {
    g.file_path_f().swap(path);g.type_f(0);
    std::fputs("[VOICE_CC] fixed announcement -> Spanish FILE\n",stderr);
   } else {
    std::string text=found->second.second,lang="en";
    g.text_f().swap(text);g.language_f().swap(lang);
    std::fputs("[VOICE_CC] Spanish file unavailable -> English TTS\n",stderr);
   }
   return;
  }
  static const std::regex battery(u8"^当前电池电量分别是([0-9]+(?:\\.[0-9]+)?)%，([0-9]+(?:\\.[0-9]+)?)%。$");
  std::smatch m;
  if(std::regex_match(g.text_f(),m,battery) && std::stod(m[1])<=100 && std::stod(m[2])<=100) {
   std::string text="Battery levels are "+m[1].str()+" percent and "+m[2].str()+" percent.",lang="en";
   g.text_f().swap(text);g.language_f().swap(lang);
   std::fputs("[VOICE_CC] battery announcement -> English TTS\n",stderr);
  }
  // Unknown messages retain every native field, including the language.
 } catch(...) {std::fputs("[VOICE_CC] localization failed; native announcement retained\n",stderr);}
}
static void* native(const char* name) {
 void* ptr=dlsym(RTLD_NEXT,name);
 if(!ptr) {std::fputs("[VOICE_CC] incompatible native ABI\n",stderr);std::abort();}
 return ptr;
}
extern "C" void copy1(Goal*,const Goal*) asm("_ZN13sys_task_msgs6action8Tts_GoalC1ERKS1_");
extern "C" void copy1(Goal* dst,const Goal* src) {
 static auto fn=reinterpret_cast<void(*)(Goal*,const Goal*)>(native("_ZN13sys_task_msgs6action8Tts_GoalC1ERKS1_"));
 fn(dst,src);apply(*dst);
}
extern "C" void copy2(Goal*,const Goal*) asm("_ZN13sys_task_msgs6action8Tts_GoalC2ERKS1_");
extern "C" void copy2(Goal* dst,const Goal* src) {
 static auto fn=reinterpret_cast<void(*)(Goal*,const Goal*)>(native("_ZN13sys_task_msgs6action8Tts_GoalC2ERKS1_"));
 fn(dst,src);apply(*dst);
}
extern "C" Goal* assign(Goal*,const Goal*) asm("_ZN13sys_task_msgs6action8Tts_GoalaSERKS1_");
extern "C" Goal* assign(Goal* dst,const Goal* src) {
 static auto fn=reinterpret_cast<Goal*(*)(Goal*,const Goal*)>(native("_ZN13sys_task_msgs6action8Tts_GoalaSERKS1_"));
 auto result=fn(dst,src);apply(*dst);return result;
}
