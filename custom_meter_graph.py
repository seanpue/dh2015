# -*- coding: utf-8 -*-
import networkx as nx
import settings
import sys
sys.path.append('./graphparser/')

from graphparser import GraphParser
from meter_graph import MeterGraph
import logging,sys
import re

# create digraph of meters (DG) using networkx
# each node has a type (=,-, and 0 [for the first one])
# the node at the end of each meter has a meter_type and meter_full_description attribute

from collections import namedtuple

ScanResult = namedtuple('ScanResult',["scan","matches", "meter_type"]) # used for completed scans

NodeMatch  = namedtuple('NodeMatch', ["node_type",       # = or -
                                      "matched_tokens",  # tokens matched at node -- could be an array
                                      "node_id",         # id of node in graph
                                      "orig_tokens",     # original tokens that were matched
                                      "ipa",
                                      "found",      # production of parser 
                                      "token_i"])        # used for matches at nodes in graph

MeterSegment = namedtuple('MeterSegment',['syllables','ending','number_of_repeats','optional','start_node','end_node'])

Branch = namedtuple('Branch',['syllables','ending','number_of_repeats','optional','weight','skip_if_matched'])

Fork = namedtuple('Fork',['segments','optional'])

OPTIONAL_BUT_PREFERRED = 2
OPTIONAL = 1
NOT_OPTIONAL = 0

phonemes ={' ': ' ',
 
 
 'aa': u'aː',
 '))': u'',
 'b': 'b',
 'bh': u'bʱ',
 ' ': u' ',
 'ch': u'tʃ',
 'chh': u'tʃʰ',
 'zh': u'ʒ',
 'i': u'ɪ',
 'a': u'ə',
 'u': u'ʊ',
 '-': u'-',
 'e': u'eː',
 '((': u'ʔ',
 '-e': u'eː',
 'ii': u'iː',
 'uu': u'uː',
 'o': u'oː',
 '-o-': u'oː',
 'ai': u'ɛː',
 'au': u'ɔː',
 'f': u'f',
 ';n': u'̃',
 'j': u'dʒ',
 'jh': u'dʒʱ',
 'l': u'l',
 'n': u'n',
 ':n': u'n',
 'h': u'ɦ',
 (';x','v'): u'kʰ',
 'sh': u'ʃ',
 'r': u'ɾ',
 'm': u'm',
 'p': u'p',
 ';h': u'ɦ',
 'ph': u'pʰ',
 'b': u'b',
 'bh': u'bʱ',
 't': u't̪',
 'th': u't̪ʰ',
 'd': u'd̪',
 'dh': u'd̪ʱ',
 ';t': u'ʈ',
 ':t': u't',
 'y': u'j',
 ';th': u'ʈʰ',
 ';d': u'ɖ',
 ';dh': u'ɖʱ',
 ';r': u'ɽ',
 ';rh': u'ɽʱ',
 'n': u'n', ### this will be the problem character
 'k': u'k',
 'kh': u'kʰ',
 'g': u'g',
 'gh': u'ɡʱ',
 'v': u'ʋ',
 'q': u'q',
 's': u's',
 ';s':  u's',
 '.s': u's',
 'z': u'z',
 "'": u'',  
 ';z': u'z',
 '.z': u'z',
 ':z': u'z',
 ';x': u'x',
 ';g': u'ɣ'}

class CustomMeterGraph(MeterGraph):
    
    def __init__(self, phrase='', count = None):

        self.DG = self.create_graph()
        self.pp = GraphParser('settings/urdu-meter.yaml',blank=' ')
        self.lp = GraphParser('settings/long.yaml',blank='b')
        self.sp = GraphParser('settings/short.yaml',blank='b')
        self.components = []
        self.count = count

        if phrase!='':
            self.init_from_phrase(phrase)
            
    def branch(self,syllables,ending=False, number_of_repeats=0, optional=False, weight=0, skip_if_matched=False):
        return Branch(syllables,ending,number_of_repeats,optional,weight,skip_if_matched)

    def create_graph(self):
        DG=nx.DiGraph()
        DG.add_node(0,type='0') # this is the start
        return DG        
       # this is the graph scan.
    
    
    def add_graph_edge(self, curr_node_ids, new_node_id,optional=NOT_OPTIONAL,weight=0):
        DG = self.DG
        for curr_node_id in curr_node_ids:
            DG.add_edge(curr_node_id,new_node_id)
            curr_type = DG.node[curr_node_id]['type']
            new_type  = DG.node[new_node_id]['type']
            edge = DG[curr_node_id][new_node_id]
            if (curr_type,new_type) in settings.bad_types:
                edge['bad_combos'] = settings.bad_types[(curr_type, new_type)]
            if optional != NOT_OPTIONAL:
                edge['optional'] = optional  #allow preference for ignoring
            edge['weight'] = weight

    def end_nodes_of_component(self, component):
        component_type = type(component).__name__
        assert component_type in ['Fork','MeterSegment']
        if component_type=='Fork':
            end_nodes = [segment.end_node for segment in component.segments]
        else:
            end_nodes = [component.end_node]
        return end_nodes
    
    def add_fork(self,branches,optional=NOT_OPTIONAL, number_of_repeats=0):
        
        fork_number_of_repeats = number_of_repeats
        logging.debug('inside add_fork, number of repeats'+str(number_of_repeats)+str(branches))
        #repeats inside fork')
        assert type(branches)==list
        for b in branches: assert type(b).__name__=='Branch'
        DG = self.DG
        if len(self.components)==0:
            prev_nodes=[0] # start from the beginning
            
            prev_optional = NOT_OPTIONAL
        else: # there are previous components
            prev_component = self.components[-1]
            prev_nodes = self.end_nodes_of_component(prev_component)
            prev_optional = prev_component.optional

        fork = Fork(segments=[],optional=optional)
        branch_starts = []
        branch_ends = []
        for branch in branches:

            curr_nodes = prev_nodes #return to original nodes
           
            start_node = len(DG.nodes())
            branch_starts.append(start_node)
            last_node = start_node - 1
            
            syllables = branch.syllables
            ending = branch.ending
            number_of_repeats = branch.number_of_repeats
            
            for i,s in enumerate(syllables):
                
                new_node = len(DG.nodes())

                DG.add_node(new_node, type=s)
                
                if i==len(syllables)-1 and ending:
                    DG.node[new_node]['ending'] = True
                
                self.add_graph_edge(curr_nodes,new_node)
                
                curr_nodes = [new_node]

                if i==0 and prev_optional!=NOT_OPTIONAL: #TODO:allow for multiple optionals
                   last_optional = len(self.components)-2
                   optionals = []
                   l = last_optional
                   optionals=[l]
#                   while l>=0 and self.components[l].optional!=NOT_OPTIONAL:
#                       optionals.append(l)
#                       l=l-1
                   for o in optionals: #this might explode
                      #TODO: THIS MAY BE BUGGY.
                      assert o > -1
                      end_nodes = self.end_nodes_of_component(self.components[o])
                      self.add_graph_edge(end_nodes, start_node,optional=True)#self.components[o].optional)
                if i+1==len(syllables):
                    branch_ends.append(new_node)
            if number_of_repeats>0:
                pass
       #DO NOT ALLOW REPEATS ON BRANCHES            
            #    if i+1 == (len(syllables)) and number_of_repeats > 0:
    #                print i, curr_node, start_node
      #              self.add_graph_edge(curr_nodes, start_node)
            m = MeterSegment(syllables=syllables, ending=ending,number_of_repeats=number_of_repeats,optional=optional,start_node=start_node, end_node=start_node+len(syllables)-1)
            fork.segments.append(m)
        if fork_number_of_repeats>0:
            logging.debug('repeats inside fork')
            for j in branch_starts:
                    self.add_graph_edge(branch_ends,j)

        self.components.append(fork)
   
    def add_segment(self,syllables, ending=False, number_of_repeats=0,optional=NOT_OPTIONAL):
        # get ends of previous nodes 
        DG = self.DG
        start_node = len(DG.nodes()) # where this segment will start
        last_node = start_node - 1 # this is the last node in the graph
        
        if len(self.components)==0:
            prev_nodes=[0] # start from the beginning
            prev_optional = NOT_OPTIONAL
        else: # there are previous components
            prev_component = self.components[-1]
            prev_nodes = self.end_nodes_of_component(prev_component)
            prev_optional = prev_component.optional

        curr_nodes = prev_nodes

        for i,s in enumerate(syllables):
            
            new_node = len(DG.nodes())

            DG.add_node(new_node, type=s)
            
            if i==len(syllables)-1 and ending:
                DG.node[new_node]['ending'] = True
            
            self.add_graph_edge(curr_nodes,new_node)
            
            curr_nodes = [new_node]

            if i==0 and prev_optional!=NOT_OPTIONAL: #TODO:allow for multiple optionals
                last_optional = len(self.components)-2

                l = last_optional
                optionals = [l]
                for o in optionals: #this might explode
                    assert o >-2
                    if  o == -1:
                        end_nodes = [0]
                    else:
                        end_nodes = self.end_nodes_of_component(self.components[o])
                    
                    self.add_graph_edge(end_nodes, start_node,optional=self.components[0].optional)
               
            if i+1 == (len(syllables)) and number_of_repeats > 0:
                self.add_graph_edge(curr_nodes, start_node)
        m = MeterSegment(syllables=syllables, ending=ending,number_of_repeats=number_of_repeats,optional=optional,start_node=start_node, end_node=start_node+len(syllables)-1)
        self.components.append(m)
    
    def graph_scan(self, in_string, parse=''): 
        #print 'in graph_scan'
        completed_scans = [] # holds complete scans
        if parse == '':
            parse = self.pp.parse(in_string) # holds output, matches
            scan_tokens = self.lp.tokenize(parse.output)
        else:
            scan_tokens = self.pp.tokenize(parse)
        logging.debug('parsed as %s',parse) 
        # this generates scan_tokens from the scan of the input string, e.g. ['b','c','v'], using the long parser (lp)
        logging.debug('scan tokens %s',scan_tokens)
#        print 'scan_tokens',scan_tokens 
        # this function descends into node (node_id), passing current token_i, matches, and a string represent
        DG = self.DG 

        def descend_node(node_id, token_i, matches, matched_so_far):
            logging.debug('descending node_id'+str(node_id))
            import operator

            successors = self.DG.successors(node_id)  #edges([node_id])
           
            newlist = sorted(successors, key=lambda k: self.DG[node_id][k]['weight'])  
            successors=newlist#.sort(key=operator.itemgetter('weight'))
            for successor_id in successors:

                if 'skip_if_matched' in self.DG[node_id][successor_id] and len(completed_scans)>0:
                    logging.debug('********skipping!')
                    continue

                node_type = self.DG.node[successor_id]['type']
                assert node_type in ('=','-')
                
                if node_type=='=': 
                      parser = self.lp
                else:
         #           print 'using sp'
                    parser = self.sp
                    if node_type=='-' and len(completed_scans)>0:
                        #if len(self.lp.match_all_at(scan_tokens,token_i))>1: # Long matches possible, so moving along
                            logging.debug('skipping wild shorts at node %d',successor_id)
                            continue
                if 'optional' in self.DG[node_id][successor_id]:# check the edge if it's optional
                    logging.debug('found an optional edge')

                for m in parser.match_all_at(scan_tokens, token_i):
                    #print '   matched ', m.tokens, m.production
                    # next, check to make sure that this is not a bad combination
                    # do so by looking for constraints on the edge
                    # note: this could be added as a constraint to match_all_at() as not_starting_with ...

                    if len(matches)>0: # if already matched something
 #                       print 'already matched'
                        a = matches[-1].found # details of previous match
                        b = m.production#**['rule']['production']   # details of current match 
                        if 'bad_combos' in self.DG[node_id][successor_id]: # if 
                             if (a,b) in self.DG[node_id][successor_id]['bad_combos']: 
                                logging.debug('found bad combos %s',(a,b))
                                continue # abort! bad combination
                    orig_tokens =[]
                    for i in range(token_i, token_i+len(m.tokens)):
                        orig_tokens +=parse.matches[i].tokens

                    # generate node_ipa
                    
                    node_ipa = u''
                    
                    for tkn in orig_tokens:
                        node_ipa +=phonemes[tkn]
                    
                    if node_ipa.endswith(u'ː̃'):#, node_ipa): # if nasal after long symbol, switch
                        node_ipa = node_ipa[0:-2]+u'̃ː'
                    if m.production.startswith('s_') and node_ipa.endswith(u'ː'):
                        node_ipa = node_ipa[0:-1]+u'ˑ' 
                    
                    
                    # advance token index based on length of match tokens
                    
                    # generate match data
                    import pdb
                    matched_tokens = m.tokens


                    match_data = NodeMatch(node_type=node_type,
                                           matched_tokens = matched_tokens,
                                           node_id=node_id,
                                           orig_tokens=orig_tokens,
                                           ipa = node_ipa,
                                           found=m.production,
                                           token_i=token_i)
                    
                    new_token_i = token_i + len(matched_tokens)

                    so_far=matched_so_far + node_type

                    curr_matches = list(matches)

                    curr_matches.append(match_data)

                    if new_token_i == len(scan_tokens):
                        logging.debug('AT THE END')
                        logging.debug(curr_matches)
                        logging.debug('node is %d%s',successor_id,self.DG.node[successor_id])


                        if 'ending' in self.DG.node[successor_id]:
                            logging.debug('AT THE END REALLY')
                            
                            count_okay = True

                            if self.count:
                                import pdb
                                pdb.set_trace()
                                count=0
                                for x in so_far:
                                    if x=='=': count+=2
                                    if x=='-': count+=1
                                if type(self.count)==list:
                                    if not count in self.count:
                                        count_okay = False
                                else:
                                    if count != self.count:
                                        count_okay = False
                            if count_okay == True:
                                completed_scans.append(ScanResult(scan=so_far, matches=curr_matches, meter_type='CUSTOM'))
                                match_node = successor_id
                            else: # count not okay
                                pass
                        else:
                            pass # doesn't match and at end, so don't continu
                    else:
                        descend_node(successor_id, new_token_i,curr_matches,so_far)
        descend_node(0, 0, [], '')
        return completed_scans

    def draw_graph(self):

        import matplotlib.pyplot as plt 
        g = self.DG

        pos=nx.spring_layout(g)
    
        plt.figure(figsize=(15,15))

        labels=dict((n,d['type']) for n,d in g.nodes(data=True)) # need to change labels for 0,1,etc.

        nx.draw(g,labels=labels,node_color='#A0CBE2',node_size=200)
        plt.show()
        

    
    def init_from_phrase(self,phrase):
        
        self.initial_phrase = phrase
        self.parse_meter(phrase)

    def parse_meter(self,phrase):

        x  = '(?:'
        x +=   '(?:'
        x +=     '(?P<required_group>\[.+?\])'+'|'
        x +=     '(?P<optional_group>\(.+?\))'
        x +=   ')'
        x +=   '(?P<repeated_group>\+)?'
        x += ')|'
        x += '(?P<regular>[=-]+)'
        
        my_re = re.compile(x)
        
        matches = [m for m in my_re.finditer(phrase)]
 
        endings = [False] * len(matches)
        
        i = len(endings)-1
        
        still_ending = True

        while still_ending == True:
            endings[i] = True
            i=i-1
            if i == 0:
                endings[i] = True
                still_ending = False
            elif matches[i].group('optional_group') is None:
                endings[i]=True
                still_ending=False


        for i,m in enumerate(matches):

            if m.group('required_group') is not None or m.group('optional_group') is not None:

                optional_on = m.group('optional_group') is not None
                repeat_on = m.group('repeated_group') is not None
                if repeat_on:
                    phrase = m.group(0)[1:-2]
                else:
                    phrase = m.group(0)[1:-1]
                internal_groups = phrase.split('|')

                logging.debug('processing group '+phrase+' optional:'+str(optional_on)+' repeat:'+str(repeat_on))
#                print 'optional = ',optional_on,'repeat',repeat_on
                
                if optional_on:
                    optional_setting = OPTIONAL
                else:
                    optional_setting = NOT_OPTIONAL

                if repeat_on: 
                    number_of_repeats = 3
                else:
                    number_of_repeats = 0
                    
                ending = endings[i]
                #.set_trace()
                if len(internal_groups)==1:
                    self.add_segment(internal_groups[0], number_of_repeats=number_of_repeats, optional=optional_setting, 
                                     ending=ending)
                
                elif len(internal_groups)>0:
                    branches = [ self.branch(j,ending=ending, number_of_repeats=number_of_repeats, weight=w) for w,j in enumerate(internal_groups)]
                    self.add_fork(branches, optional = optional_setting, number_of_repeats=number_of_repeats)
            else:
                self.add_segment(m.group(0), optional=NOT_OPTIONAL,ending=endings[i])
#               print 'non-group found', m.group(0)
               
def test_graph():
    mg = CustomMeterGraph()

    mg.add_fork([mg.branch('=-=='),
                 mg.branch('--==',weight=1,skip_if_matched=True)],
                 optional= NOT_OPTIONAL)

    
    mg.add_fork([mg.branch('--=', ending=True, number_of_repeats=2),
                 mg.branch('==',  ending=True)],
                 optional= NOT_OPTIONAL)
    
    mg.add_segment('-',ending=True,optional=OPTIONAL)

    return mg
if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
#[]()#
    hindi_scanner = CustomMeterGraph('[=|=-=-|-=-=][=|--|-=-=]+=(-)]',count=32)

    hindi_scanner.graph_scan(' ul;tii ho ga))ii sab tadbiire;n kuchh nah davaa ne kaam kiyaa')
