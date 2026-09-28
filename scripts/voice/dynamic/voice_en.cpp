// Interpose only TtsClient::on_send. Original FILE goals and failure behavior stay native.
#include "tts_abi.hpp"
#include <dlfcn.h>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include "translations.hpp"

namespace voice_en {
bool chinese(const std::string& text) {
  // Decode UTF-8 enough to recognize CJK; non-Chinese languages are not translated.
  for (size_t i=0;i<text.size();) {
    unsigned char c=text[i++];unsigned cp=c;int n=0;
    if ((c&0xE0)==0xC0){cp=c&31;n=1;}else if((c&0xF0)==0xE0){cp=c&15;n=2;}else if((c&0xF8)==0xF0){cp=c&7;n=3;}
    while(n-- && i<text.size())cp=(cp<<6)|(static_cast<unsigned char>(text[i++])&63);
    if((cp>=0x3400&&cp<=0x9fff)||(cp>=0xf900&&cp<=0xfaff)||(cp>=0x20000&&cp<=0x3134f))return true;
  }return false;
}
bool translate(const std::string& input,std::string& out) {
  auto it=translations.find(input);
  if(it!=translations.end()){out=it->second;return true;}
  if(!chinese(input)){out=input;return true;}
  // Exact clauses only. Never invent a translation for an unknown error.
  std::string result;size_t begin=0;
  while(begin<input.size()) {
    size_t ascii=input.find(',',begin),wide=input.find("，",begin);
    size_t end=std::min(ascii,wide);size_t separator=(end==wide?3:1);
    std::string clause=input.substr(begin,end==std::string::npos?end:end-begin);
    if(!clause.empty()) {
      auto found=translations.find(clause);
      if(found!=translations.end())clause=found->second;
      else if(chinese(clause))return false;
      if(!result.empty())result+=' ';result+=clause;
    }
    if(end==std::string::npos)break;
    begin=end+separator;
  }
  if(result.empty())return false;out=result;return true;
}
void apply(sys_task_msgs::action::Tts_Goal& goal) noexcept {
  if(goal.type_f()!=1)return;
  try {
    std::string translated;
    if(!translate(goal.text_f(),translated)) {
      std::fputs("[VOICE_EN] unmapped Chinese; original goal retained\n",stderr);return;
    }
    // Construct first; swaps cannot throw, so failures leave the original goal intact.
    std::string language="en";
    goal.text_f().swap(translated);goal.language_f().swap(language);
  } catch(...) { std::fputs("[VOICE_EN] localization failed; original goal retained\n",stderr); }
}
}
namespace task_manager {
class TtsClient {public:void on_send(sys_task_msgs::action::Tts_Goal&);};
void TtsClient::on_send(sys_task_msgs::action::Tts_Goal& goal) {
  using Callback=void(*)(TtsClient*,sys_task_msgs::action::Tts_Goal&);
  static Callback original=[] {
    void* h=dlopen("/opt/walker/task_manager/lib/libtask_manager_lib.so",RTLD_LAZY|RTLD_NOLOAD);
    void* p=h?dlsym(h,"_ZN12task_manager9TtsClient7on_sendERN13sys_task_msgs6action8Tts_GoalE"):nullptr;
    if(!p)throw std::runtime_error("VOICE_EN: native callback unavailable");
    return reinterpret_cast<Callback>(p);
  }();
  original(this,goal); // Native input validation and exceptions occur unchanged, first.
  voice_en::apply(goal);
}
}
extern "C" void voice_en_apply_test(sys_task_msgs::action::Tts_Goal* goal){voice_en::apply(*goal);}
