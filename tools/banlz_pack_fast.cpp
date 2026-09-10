// Native implementation of tools/banlz.py's greedy token format.
// Compile: g++ -O3 -std=c++17 banlz_pack_fast.cpp -o banlz_pack_fast.exe
// Usage: banlz_pack_fast input.bin output.bin [candidate-limit]
// Output must still pass banlz_strict.verify before use on a disc.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
using Bytes=std::vector<unsigned char>;
void var(Bytes& out,unsigned v){ Bytes tmp; do{tmp.push_back((v&127)<<1);v>>=7;}while(v); std::reverse(tmp.begin(),tmp.end());tmp.back()|=1;out.insert(out.end(),tmp.begin(),tmp.end()); }
struct Token{int pos,len,dist;};
int main(int argc,char**argv){
 if(argc<3)return 2;
 std::ifstream f(argv[1],std::ios::binary);if(!f)return 3;
 Bytes d((std::istreambuf_iterator<char>(f)),{});int n=int(d.size());
 if(!n)return 4;
 int limit=argc>3?std::stoi(argv[3]):768;
 std::vector<int> head(1<<24,-1),prev(n,-1);
 for(int i=0;i+2<n;i++){int key=d[i]|(d[i+1]<<8)|(d[i+2]<<16);prev[i]=head[key];head[key]=i;}
 auto match=[&](int p){
  int best=0,dist=0;
  if(p+2<n){
   int tried=0;
   for(int c=prev[p];c>=0&&tried<limit&&p-c<=4194304;c=prev[c],++tried){
    if(best && p+best<n && d[c+best]!=d[p+best])continue;
    int len=3;
    while(p+len+8<=n){uint64_t a,b;std::memcpy(&a,&d[c+len],8);std::memcpy(&b,&d[p+len],8);if(a!=b)break;len+=8;}
    while(p+len<n&&d[c+len]==d[p+len])++len;
    if(len>best){best=len;dist=p-c-1;if(len>=4096)break;}
   }
  }
  if(best<2)for(int c=std::max(0,p-8);c<p;c++){
   int len=0;while(p+len<n&&d[c+len]==d[p+len])++len;
   if(len>best&&len>=2){best=len;dist=p-c-1;}
  }
  return Token{p,best,dist};
 };
 std::vector<Token> ts;int i=0,lit=0;
 if(argc>4){
  // Bounded dynamic parse avoids the quadratic scans in the Python fallback.
  std::vector<double> dp(n+1,0);std::vector<Token> pick(n);
  std::vector<int> run(n,1);for(int p=n-2;p>=0;--p)if(d[p]==d[p+1])run[p]=run[p+1]+1;
  auto cost=[](int dist,int len){int c=1;if(dist>7){do{++c;dist>>=7;}while(dist>7);}if(len>16){unsigned v=len-1;do{++c;v>>=7;}while(v);}return c;};
  for(int p=n-1;p>=0;--p){
   dp[p]=dp[p+1]+1.04;pick[p]={p,0,0};
   auto consider=[&](int len,int dist){if(len<2)return;double c=cost(dist,len)+dp[p+len];if(c<dp[p]){dp[p]=c;pick[p]={p,len,dist};}};
   if(p&&d[p]==d[p-1]){consider(run[p],0);consider(std::min(16,run[p]),0);}
   if(p+2>=n)continue;
   // Long identical-byte runs are already represented optimally by distance 0.
   if(p&&d[p]==d[p-1]&&run[p]>4096)continue;
   int tried=0;
   for(int c=prev[p];c>=0&&tried<limit&&p-c<=4194304;c=prev[c],++tried){
    int len=3,maxlen=std::min(n-p,4096);
    while(len+8<=maxlen){uint64_t a,b;std::memcpy(&a,&d[c+len],8);std::memcpy(&b,&d[p+len],8);if(a!=b)break;len+=8;}
    while(len<maxlen&&d[c+len]==d[p+len])++len;
    int dist=p-c-1;
    consider(len,dist);consider(std::min(len,16),dist);consider(std::min(len,8),dist);
    if(len==maxlen&&len>=4096)break;
   }
   for(int delta=1;delta<=8&&delta<=p;++delta)if(d[p]==d[p-delta]&&p+1<n&&d[p+1]==d[p-delta+1])consider(2,delta-1);
  }
  while(i<n){auto m=pick[i];if(m.len){if(i>lit)ts.push_back({lit,i-lit,-1});ts.push_back(m);i+=m.len;lit=i;}else ++i;}
 }else while(i<n){
   auto m=match(i);
   if(m.len){
    if(i+1<n){auto next=match(i+1);if(next.len>m.len+1){++i;m=next;}}
    if(i>lit)ts.push_back({lit,i-lit,-1});
    ts.push_back(m);i+=m.len;lit=i;
   }else ++i;
 }
 if(i>lit)ts.push_back({lit,i-lit,-1});
 Bytes out;var(out,n);var(out,29);var(out,0);
 for(size_t k=0;k<ts.size();){
  Token t=ts[k++];if(t.dist!=-1)return 5;
  size_t start=k;while(k<ts.size()&&ts[k].dist>=0)++k;
  unsigned refs=unsigned(k-start),rf=refs==0?1:(refs>15?0:refs);
  out.push_back((rf<<4)|(t.len>15?0:t.len));
  if(t.len>15)var(out,t.len);if(refs>15)var(out,refs);
  out.insert(out.end(),d.begin()+t.pos,d.begin()+t.pos+t.len);
  for(size_t j=start;j<k;j++){
   unsigned dist=ts[j].dist;Bytes chunks;
   do{chunks.push_back(dist&127);dist>>=7;}while(dist);
   std::reverse(chunks.begin(),chunks.end());
   int nib;
   if(chunks.size()==1&&chunks[0]<=7){nib=(chunks[0]<<1)|1;chunks.clear();}
   else{if(chunks[0]>7)chunks.insert(chunks.begin(),0);nib=chunks[0]<<1;chunks.erase(chunks.begin());for(auto&v:chunks)v<<=1;chunks.back()|=1;}
   int len=ts[j].len-1;out.push_back(((len<=15?len:0)<<4)|nib);out.insert(out.end(),chunks.begin(),chunks.end());if(len>15)var(out,len);
  }
 }
 std::ofstream o(argv[2],std::ios::binary);o.write(reinterpret_cast<const char*>(out.data()),out.size());if(!o)return 6;
 std::cout<<n<<" -> "<<out.size()<<" bytes\n";
}
