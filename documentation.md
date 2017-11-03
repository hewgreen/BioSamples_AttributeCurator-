#JOBS

DELETE THIS SECTION WHEN THE JOBS ARE DONE.

DOC
- THIS DOC HAS NOT BEEN SPELL CHECKED!
- UPDATE INPUT SECTION AFTER REWRITEING THE CODE WITH SPECIFICS ABOUT FORMATS
- would be good to add some images of analysis showing non-normal distributions etc

CODE
- AT END. ADD IN GOLBAL PRINT STATEMENTS TO TELL THE USER WHAT IS HAPPENING. GENERALLY I WANT TO MINIMISE THESE AND PUSH MOST PRINTING TO LOG FILE.
- AT END. CREATE A VERBOSE GLOBAL LOG FILE TO SHOW WHAT HAPPENED IN THE RUN
- WHY DOES EDGE WEIGHT COME UP AS 0 SOMETIMES OR None OTHERS? CHECK AND FIX
- IS EDGE WEIGHT BROKEN? I'M SEEING LOTS OF 0. MAKE SURE THIS ISNT A BROKEN CALCULATION.
- IS THERE A MORE ELEGANT WAY OF CHECKING IF A NODE HAS AN ATTRIBUTE OTHER THAN except KeyError:?
- ADD TIMESTAMP ENTITY TO NEO WHEN EACH STATS SCRIPT IS RUN
- NEED TO ADD A PARAMETER OPTION TO UPDATE CALCULATIONS EVEN IF THEY HAVE PREVIOUSLY BEEN MADE
- NEED TO BE ABLE TO SWAP BAD/GOOD FACET IN APP OR SELECT BOTH BAD. IF BOTH GOOD IT'S NO MERGE.
- NEED MANCLUSTER TO PRODUCE MEDIAN EXAMPLES OF CLUSTER SAMPLES TO AID DECISION MAKING.

## v1.1 Suggestions

- add ontology script as another early stage filtering mechanism. Hopefully this script will broadly pull pairs into the analysis pipeline.
- prevent missing data (reported in graph_make.py) by altering input.py order of data aquisition. Check this is the only issue here.
- add more progress bars


# BioSamples Attribute Curator Documentation

**A semi-automated curation tool to identify and harmonise erronious attributes in the BioSamples database.**

### Scope

The digital BioSamples database aims to aggregate sample metadata from all biological samples used throughout the world and serve as a central hub for linking and relating this metadata to biological data. To this end, it does not enforce information requirements, thereby lowering the barrier to entry for researchers; this also widens the scope of metadata collection. The downside to a zero validation design is the potential for low quality input which has a negative impact on search and information output. Therein lies the need for this software. As of October 2017 BioSamples has over 4.7\times10^6 samples sharing over 27,000 attributes and is quickly growing.

The scope of this software does not extend to curation of the values associated with these attributes but it does explore the value data as one potential way of comparing attributes. Here we aim to use a holistic semi-automated approach to clean up the attributes and merge those which have been provided in error. This includes harmonising various cases of lexical disparity including case differences, spelling errors and pluralisation). It also uses ontology comparisons (of attibutes and associated values) to explore merge oppotunities as well as various statistical distances (including attribute coexistance and lexical similarity scoring of value information).

After identification of possible curatable attribute pairs, we extrapolate clusters of samples to ensure curations are only applied to relevent samples. This improves our confidence and flexibility. Automated and semi-automated analysis are recorded and remembers in a clearly accesible way to avoid duplicate computation and provide data for correlation analysis (and other machine learning methods). This latter analysis should dramatically improve the power of this tool and is an essential component in it's design.

### Beyond Immediate Scope

* Ontology cleanup- although not directly considered this will inevitably be improved through use of this tool.
* Profiling of samples- although clustering methods herein could be adapted to meet this goal.
* Checking external links and references- this should be encorporated when possible (relates to profiling samples).
* Replacing value information- although the methods herein can be adapted this would ideally operate as a separate pipline as specific considerations differ.

## Scripts


### main.py

Controlling script. Imports other scripts. Decides when to generate new input. Launches analysis scripts in correct order. Amalgamates results. Stores and edits output files.

#### Organisation
Broadly the pipeline operates as such:

input -> pair filtering -> analysis -> clustering -> human input -> curation items

* input- generate input files required if they are old
* pair filtering- pairwise scripts that are fast enough to analyse every pair and suggest merge oppotunities^*
* analysis- including coexistance graph analysis and value matching distances. These scripts also generate pairwise distances but they tend to be slower. Therefore they are applied to a pre-trimmed list of pairs.
* clustering- samples affected by suggested merges are clustered to ensure homogeneity before merging. At this stage it is also possible to apply the curations to specific samples. 
* human input- human curators are presented with various data to make merge decisions.
* curation items- the output is a list of sample specific attribute merges ready to be turned into curation items.

^* note that the lexical script does much more than filter results. It also XXXXXXXX

Scriptwise pipe:

input.py -> lexical.py -> coexistance.py -> values.py -> cluster.py

#### Output

### input.py

Generates inputs for pipeline and stores output into ./data as csv or json. This script makes 4 files:

1. attributes.csv
csv list of attributes and their frequency of occurance in the database

2. samples.csv
csv with sampleID folowed by all the attributes that sample contains

3. coexistences.json
list of all pairs that coexist in the same sample and the frequency at which they do so

4. values
list of dictionaries containing key:value pairs as attribute:[value], with values stored as a list


The 'attribute.csv' is generated quickly (XXXXXX time) as it only requires 1 Solr request. This file is only used for XXXXXX. 'samples.csv' is generated by iterative page requests through BioSamples v3 API and scrapes each page. This process is multithread enabled to speed up the process but this is still a process that takes longer than 8 hours. The temporary threads this process produces are concatinated to produce 'samples.csv'. The sampleID is then stripped from each line and the output is then used to feed the modules that count the coexistance which ultimately builds 'coexistences.json'.

This script then does some pre-processing of the data. It converts the json into csv format (coexistences.csv)

### graph_make.py

This pre-processing script uses __attributes.csv__ and __coexistences.json__ to calculate weighting and create a networkX graph. This output is stored in three files:

1. coexistences.csv
This is a csv converted directly from the json using re. While this may be prone to breaking and would ideally be replaced with a json reader, unfortunately there are issues due to the flat structure of the json file.
2. coexistencesProb.csv
Pandas is used to lookup attribute frequencies and calculte expected coexistance counts. These can be compared to expected coexistance counts to calculate a weight (see below for more details).
3. coexistences.gexf
NetworkX graph output suiltable for reading by Gephi (see _A note on Gephi_).

#### Why do we require probability weighting?

If two attributes coexist frequently within samples we may presume they are related and provide distinct information. We could conclude that these facets should not be merged becuase they provide distinct information (this can be confired by checking value data too). However, numerous attributes in the BioSamples Database (such as organism, synonym, model, package, organismPart and sampleSourceName) will coexist with each other in samples more frequently than less numerous ones. Therefore, to derrive the significance of the coexistance count we must normalise against individual attribute frequencies.

In order to do this we calculate the following steps:

1. probability of attribute = no of instances / total instances
1. expected coexistance count = probability of attribute1 * probability of attribute2 * total instances
1. difference = observed coexistance count - expected coexistance count 
1. weight = difference / sum of differences

As BioSamples Data input is not randomly generated the vast majority of attributes do not contain any coexistance within samples and the vast majority that do have a positive difference (observed higher than expected). The graph is undirected even though Gephi insists on adding direction depending on which attribute is the 'source' or 'target' but this is only a visualisation bug. All weights add up to 1 (as per caculations outlined above) and the graph contains both positive and negative weights (negative when expected is higher than observed). These negative weights are often intuitively relevent (e.g. organismPart and serovar with a difference of -27689 or environmentBiome and organismPart with a difference of -89490) and highly positive weights are also intuitive (e.g. depth and elevation with a difference of 99617).

#### Missing value warnings.

Missing attributes may occur if the pair has an attribute that is not in attributes.csv. The number of missing pairs is recorded. To minimise this, attributes.csv is generated as the last step in the input.py. This should be checked to ensure significant data isn't missing. This process may need to be more stringent in later versions.

#### A note on using Gephi.

Gephi is an open-source free graph visualisation program for windows, mac and linux. Download at https://gephi.org

1. When you load this into Gephi you must first insist that the 'weight' column becomes the edge weight. This can be done in the Data Laboratory with the 'Copy Data to Other Column' button intuitively. I also add these values to the label column so that I can see the values if I request them in the graph.

2. I suggest starting by changing the size of the node to be equivelent to 'Degree' aka how many edges that facet has. I followed this method https://stackoverflow.com/questions/36239873/change-node-size-gephi-0-9-1

For general help see this: https://gephi.org/tutorials/gephi-tutorial-visualization.pdf

3. The next step is the layout. There are three relevent algorithms for expanding the nodes. Here are my observations on each, WARNING this is a very reductive description:

YifanHu(Proportional)

Seems the most intuitive so you can work out why things appear where they do. this is because the whole thing is a minimisation calculation based on the weights. Thats why its a circle, why big stuff tends to stay in the middle and the weakest linked stuff floats to the outer asteroid belt of junk. I reccomend starting with this because you can undertand what it is doing but it is not the best for getting discreet clusters.

OpenOrd

This does not give an intuitive result but it does make nice clusters for various reasons. It is supposedly the quickest but all these three work well enough with the dataset we have. It is great to watch it going through the various stages and would be perfect for a live demo.

ForceAtlas(2)

Default settings are nice and gives you somthing inbetween the two above. I changed a few parameters to get the largest nodes out the the edge of the screen so I could focus on smaller clusters in the middle. To do this switch on LinLog mode.


### lexical.py

Current output:

"merge_confirmed_"+TIMESTAMP+".csv"
"merge_after_manual_review_"+TIMESTAMP+".csv"

analysis pipeline currently takes:
'data/mergeHighConfidence.csv' and 'data/mergeLowConfidence.csv'


Trish's version:

needs:
* "../master-data/cocoa_facets.csv"
* "en_US","../master-data/biosamples-lexical-dictionary/lowercase_mywords.txt"


### coexistance.py

needs graph_make.py to be run first
input:
* query pairs from files starting with merge
* fold_diff_weighted_network.gexf

pulls in all csv starting with 'merge'

output:
mergeHighConfidence_stats.csv
mergeLowConfidence_stats.csv

I'm hoping I can iteratively add to these files as I feed them to each stats module.

has -r ability vs the usual continue mode
- need to add all its outputs here and what they mean

### values.py

- takes data/values.csv as input (currently I'm working with a temp file that Trish generated I need to build this with the input script)
- lots more info is calculated for the fuzzy score if needed!
- has -r ability vs the usual continue mode
- need to add all its outputs here and what they mean

### auto_cluster.py

This scipt performs clustering up to the point of k (cluster number) determination. Whilst various automated methods exist to determine k, they are unsuitable on the highly variable BioSample dataset. Therefore, this script aims to equip the user with as much information as possible to make a judgement on k. After k has been manually entered the mancluster.py script can then perform further calculations and provide information on individual clusters such as median sample representations of that cluster. This module requres the input data from 'samples.csv'. If this program is run in recalculate mode (-r argument passed) it will strip Sample-Cluster relationships that were previously calculated rather than skipping previously calculated Pairs. Therefore when ran in normal mode, the scipt will essentially pick up where it left off.   

The clustering that can be done automatically prior to a user entered k includes:

* tally of no. of samples which have each or both attributes
* generation of a binary matrix (samples vs attribute presence/absence)
* 2D reduction (MCA) of the binary matrix and plotting of scatter graph
* hiarachical clustering and plotting dentrogram

N.B. When running in normal mode the script won't know if there are any missing samples as it will skip over any Pairs that have previously been calculated. Therefore, it is important to schedule this script in -recalculate mode to ensure extra samples are linked to on a regular basis.

#### The output of this script for each Pair in the Neo4j graph

Added to Pair node:
1. total no of samples in pair
1. no of samples in attribute 1
1. no of samples in attribute 2
1. no of shared samples in pair
1. file path for MCA scatter plot
1. file path for hiarachical clustered dendrogram

Relationships added:
1. Adds a direct relationship (HAS_ATTRIBUTE) from the Pair nodes to relevant Sample nodes. These are not removed when k has been determined in a later step. 

The scatter plot from MCA is generated and saved in 'data/plots/...' for later recall along with the coordinates from the MCA analysis (files named mca_id.log). The log file is a csv with columns x and y coordinates as well as the frequency (s)of samples at that coordinates. These are samples with identical attributes.

#### Further work

- add more automated k methods aiming to identify a fully automated method.
- review dendrogram plot asthetics
- after k has been manually determined k-means clustering needs to work from xD data not 2D data hence autoclus needs to pass on the binary matrix?
- calculates the number of samples affected by the merge. this needs to be used to rank when human curators see facets.


### man_cluster.py

This script will only trigger when a user has entered a k. It should be able to run automatically but mainly on demand via the app. When k is entered this script should fire and produce results ASAP for that facet. If the user changes their mind it should trigger again. The automatic firing of this should update and mop up anything that is old or hasn't been calculated.

#### Choosing a clustering method

Everyone loves K-means but unfortiantely it is not an appropreate method for clustering dichotomous data. This is because the Euclidean distance will only be a count of the binary differences between samples. This means that inappropreate ties may occur which cannot be overcome in iterative cluster assignments. Hence, we shouldn't use k-means for clsutering binary data.

Appropriate alternatives are hierarchical clustering (as implemented by autocluster.py), two step clustering or spectral clustering. Or one can use MCA (which is better than PCA for binary data) to reduce the binary data into a number of dimensions which also serves to convert it from being binary (this is the first step of spectral clustering anyway). Then k-means is an appropreate clustering method too.

In summary, generally dimension reduction (via calculation of eigenvalues) is required before clustering binary data. This step is done in autocluster to 2D. More dimensions improve resolution but this hinders plotting. It is however useful when used as a backend to clustering.

### Neo4J Curation Database

This stores the output from all the scripts.

- pairs are sorted alphabetically prior to node creation to prevent duplication of reverse pairs.
- before I have the lexical script working I need to manually create the pairs from the lexical script to give me a platform to get the other scripts working.


















