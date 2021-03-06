# ViQUF

New algorithm for full viral haplotype reconstruction and abundance estimation. It is an alternative approach for the first developed approach viaDBG which was based entirely on **de Bruijn** graphs. ViQUF is based on flow networks which allows us to do a proper and successful estimation of the strains frequencies. 

The overall workflow is as follows:

* Building assembly graph (BCALM)
* Polishing the assembly graph by:
	* Classifying edges as weak and strong, and removing the weak ones called as filigree edges.
	* Removing isolated nodes.
	* Removing short tips.
* Paired-end association.
* Paired-end polishing removing as many wrong associations as possible.	
* Core algorithm:
	* For every pair of adjacent nodes A -> B, we built a DAG from their paired-end information.
	* DAG is translated into a flow network and a min-cost flow is solved.
	* The flow is translated into paths via a "greedy" path heuristic. 
* Final strains are build following two rules:
	* Standard contig traversion (deprecated)
	* Min-cost flow over the Approximate Paired de Bruijn Graph built from the core algorithm.

# Depedencies

* Python 3.* - we encourage you to build a conda environment and still all dependencies via conda: conda create -n ViQUF-env python=3.6
	* Biopython, altair, gurobi 
	* matplotlib, scipy, numpy
* C++17
* SDSL
* BCALM
* quast 4.3 or quast 5.0.1 to evaluate the results
* Compile: make clean && make

## Command line standard:

The file **execution-script** contains an example about how to execute the code.

* python scripts/testBcalm.py $1 $2 10 ngs $3 $4 --no-meta
	* $1 - folder with NGS reads
	* $2 - kmer size
	* $3 - --correct/--no-correct to perform correction or not respectively
	* $4 - --join, has pear been executed? If so --join otherwise --no-join
* ./bin/output.out tmp/unitigs.FM placements tmp 121 tmp/unitigs.graph tmp/unitigs.unitigs.fa tmp/unitigs-viadbg.fa tmp/Ownlatest/append.fasta $5 $6 --virus
	* $5 - complete set of reads (it is not mandatory but recommended)
	* $6 - --debug or not.
* python scripts/post-process.py


