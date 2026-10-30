/* AGPL-3.0-or-later; regression tests for the Olaf matcher fork. */
#include <assert.h>
#include <string.h>
#include "../src/olaf_fp_matcher.c"
static size_t hits;
static uint64_t seen_lo, seen_hi;
size_t olaf_db_find(Olaf_DB *db,uint64_t lo,uint64_t hi,uint64_t *out,size_t cap){
 (void)db;seen_lo=lo;seen_hi=hi;
 size_t n=hits<cap?hits:cap;
 for(size_t i=0;i<n;i++) out[i]=((uint64_t)100<<32)|7;
 return n;
}
void olaf_db_find_meta_data(Olaf_DB *db,uint32_t *id,Olaf_Resource_Meta_data *m){
 (void)db;(void)id;memset(m,0,sizeof(*m));
}
uint64_t olaf_fp_extractor_hash(struct fingerprint f){(void)f;return 42;}
int main(void){
 Olaf_Config *c=olaf_config_default();assert(c);
 c->maxDBCollisions=4;c->independentTimeVotes=true;c->skipSaturatedHashes=true;
 Olaf_FP_Matcher *m=olaf_fp_matcher_new(c,NULL,NULL);assert(m);
 hits=4;olaf_fp_matcher_match_single_fingerprint(m,200,42);
 assert(hash_table_num_entries(m->result_hash_table)==0);
 hits=3;olaf_fp_matcher_match_single_fingerprint(m,200,0);
 assert(seen_lo==0 && seen_hi==(uint64_t)c->searchRange);
 uint64_t key=((uint64_t)25<<32)|7;
 struct match_result *v=hash_table_lookup(m->result_hash_table,&key);assert(v && v->matchCount==1);
 olaf_fp_matcher_match_single_fingerprint(m,201,UINT64_MAX);
 assert(seen_hi==UINT64_MAX && v->matchCount==2);
 olaf_fp_matcher_match_single_fingerprint(m,200,42);assert(v->matchCount==2);
 c->independentTimeVotes=false;
 olaf_fp_matcher_match_single_fingerprint(m,201,42);assert(v->matchCount==5);
 c->skipSaturatedHashes=false;hits=4;
 olaf_fp_matcher_match_single_fingerprint(m,201,42);assert(v->matchCount==9);
 olaf_fp_matcher_destroy(m);olaf_config_destroy(c);
 puts("matcher v3 regressions passed");return 0;
}
