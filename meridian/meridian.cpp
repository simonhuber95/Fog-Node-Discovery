double* RingManageQuery::createLatencyMatrix() { 		
	int N = remoteNodes.size();	// Dimension of matrix all k+l nodes
	//	Allocate the matrix here
	double* latencyMatrix = (double*) malloc(sizeof(double) * N * N);		
	if (latencyMatrix == NULL) {
		return NULL;
	}	
	set<NodeIdent, ltNodeIdent>::iterator outerIt = remoteNodes.begin();		
	//	Create coordnates for each of these nodes
	for (u_int i = 0; outerIt != remoteNodes.end(); outerIt++, i++) {
		set<NodeIdent, ltNodeIdent>::iterator innerIt = remoteNodes.begin();
		for (u_int j = 0; innerIt != remoteNodes.end(); innerIt++, j++) {
            // Double for loop to iterate over latency matrix to fill it up
			if (i == j) {
                // diagonal is 0
				latencyMatrix[i * N + j] = 0.0;				
			} else {
                // map with all the node and u_int is the latency
				map<NodeIdent, map<NodeIdent, u_int, ltNodeIdent>*, 
						ltNodeIdent>::iterator thisNodeMapIt 
					= RetNodeMap.find(*outerIt);
                    // some weird C++ stuff, just ignore				
				if (thisNodeMapIt == RetNodeMap.end()) {
					ERROR_LOG("Outer member not found: createLatMatrix\n");
					free(latencyMatrix);
					return NULL;
				} else {
					map<NodeIdent, u_int, ltNodeIdent>* thisNodeMap = 
						thisNodeMapIt->second;				
					map<NodeIdent, u_int, ltNodeIdent>::iterator findCur =
						thisNodeMap->find(*innerIt);
					if (findCur == thisNodeMap->end()) {
						ERROR_LOG("Inner member not found: createLatMatrix\n");
						free(latencyMatrix);
						return NULL;
					} else {
						// Stored latency in milliseconds from node i to node j
						latencyMatrix[i * N + j] = findCur->second / 1000.0;
					}
				}
			}
			WARN_LOG_1("%0.2f ", latencyMatrix[i * N + j]);
		}
		WARN_LOG("\n");
	}
	return latencyMatrix;
}


double RingManageQuery::reduceSetByN(
					vector<NodeIdent>& inVector,	// Vector of nodes
					vector<NodeIdent>& deletedNodes,
					int numReduction,				// How many nodes to remove
					double* latencyMatrix){			// Pointer to latencyMatrix

	int N = inVector.size();	// Dimension of matrix
	int colSize = N;
	int rowSize = N;	
	double maxHyperVolume = 0.0;
	//	Perform reductions iteratively
    // iterate over the amount of reductions
	for (int rCount = 0; rCount < numReduction; rCount++) {
		bool maxHVNodeFound	= false;
		NodeIdent maxHVNode = {0, 0};
		double maxHV	= 0.0;
		maxHyperVolume	= 0.0; // Reset		

		/*	Iterate through the nodes to calculate the hyperVolume for each node to be removed
		*/		
		for (u_int k = 0; k < inVector.size(); k++) {

			//	Swap out the current working column with the last column
            // then reduce the column size by 1
            // so basically we just ignore the curren working column
			for (int i = 0; i < rowSize; i++) {
				double tmpValue = latencyMatrix[i * N + k];
				latencyMatrix[i * N + k] = latencyMatrix[i * N + colSize - 1];
				latencyMatrix[i * N + colSize - 1] = tmpValue;
			}
			colSize--;			
			//	And the corresponding row information
            // also swap out the corresponding row with the last row 
            // and ignore it again by saying there is one less row
			cblas_dswap(colSize, 
				&latencyMatrix[k * N], 1, &latencyMatrix[(rowSize-1) * N], 1);
			rowSize--;
			assert(rowSize == colSize);
			//	Calcuate the hypervolume without this node
			double hyperVolume = calculateHV(N, rowSize, latencyMatrix);
			/*	See if it is the minimum so far
				Rationale:	By removing this node, we still have the maxHV
							comparing to removing any other node. Therefore,
							we want to remove this node to keep a big HV
			*/
			if (hyperVolume >= maxHV) {
				maxHVNodeFound 	= true;
				maxHVNode 		= inVector[k];
				maxHV 			= hyperVolume;
			}
			//	The max hypervolume at this reduction level
			if (hyperVolume > maxHyperVolume) {
				maxHyperVolume = hyperVolume;
			}
			//	Undo row and column swap
			rowSize++;			 
			cblas_dswap(colSize, 
				&latencyMatrix[k * N], 1, &latencyMatrix[(rowSize-1) * N], 1);
			colSize++;
			for (int i = 0; i < rowSize; i++) {
				double tmpValue = latencyMatrix[i * N + k];
				latencyMatrix[i * N + k] = latencyMatrix[i * N + colSize - 1];
				latencyMatrix[i * N + colSize - 1] = tmpValue;
			}
		}
		if (maxHVNodeFound == false) {
			//	Could not reduce any further, all anchors
			assert(false); // This shouldn't really happen for any valid case 
			return 0.0;
		}
		//	For the node that we have removed, remove it from the latency
		//  matrix as well as from the vector of nodes
		for (u_int k = 0; k < inVector.size(); k++) {
			if ((inVector[k].addr == maxHVNode.addr) && 
					(inVector[k].port == maxHVNode.port)) {
				for (int i = 0; i < rowSize; i++) {
					double tmpValue = latencyMatrix[i * N + k];
					latencyMatrix[i * N + k] = latencyMatrix[i * N + colSize - 1];
					latencyMatrix[i * N + colSize - 1] = tmpValue;
				}
				colSize--;								
				cblas_dswap(colSize, 
					&latencyMatrix[k * N], 1, &latencyMatrix[(rowSize-1) * N], 1);
				rowSize--;
				deletedNodes.push_back(inVector[k]);
				inVector[k] = inVector.back();
				inVector.pop_back();
			}
		}
	}
	return maxHyperVolume;
}


double RingManageQuery::calculateHV(
	const int N,			// Physical size of the latencyMatrix
	const int NPrime,		// Size of the latencyMatrix in use
	double* latencyMatrix)	// Pointer to latencyMatrix
{
	/*	Time to perform Gram Schmidt to reduce the dimension by 1
	*/
	GramSchmidtOpt gs(NPrime);

	/*	tmpModMatrix is the latencyMatrix where every row subtracts
		the last row in the matrix (and the last row is all 0)
	*/
	double* tmpModMatrix = 
		(double*)malloc(sizeof(double) * NPrime * NPrime);

	for (int i = 0; i < NPrime - 1; i++) {
		// Copy from latencyMatrix to tmpModMatrix
		cblas_dcopy(NPrime, 
			&latencyMatrix[i * N], 1, &tmpModMatrix[i * NPrime], 1);
        
        // subtract the last row from every other row
		// Perform the subtraction
		cblas_daxpy(NPrime, -1.0, &latencyMatrix[(NPrime-1) * N], 
			1, &tmpModMatrix[i * NPrime] , 1);

        // then add each row as a vector to the GS
		gs.addVector(&tmpModMatrix[i * NPrime]);
	}

	/*	Zero out last row explictly
	*/
	for (int i = 0; i < NPrime; i++) {
		tmpModMatrix[(NPrime-1) * NPrime + i] = 0.0;
	}
			
	/*	Retrieve the orthogonal matrix that has been computed
	*/
	int orthSize;
	double* orthMatrix = gs.returnOrth(&orthSize);

	/*	Now re-create the latency matrix based on the dot product
	*/
	coordT* latencyMatrixMod = 
		(double*) malloc(sizeof(double) * orthSize * NPrime);

    // Multiplies the tmpModMatrix with the latencymatrix two matrices 
    // tmpModMatrix is not transposed
    // latencyMatrix is transposed
    // Result is stored in latencyMatrixMod
	cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasTrans,
		NPrime, orthSize, NPrime, 1.0, tmpModMatrix, NPrime, 
		orthMatrix, NPrime, 0.0, latencyMatrixMod, orthSize);

	free(tmpModMatrix); // No no longer useful, can delete

	/*	Let's get the hypervolume
	*/
    // calculate the volume of the new matrix
	double hyperVolume = 
		getVolume(latencyMatrixMod, orthSize, NPrime);

	free(latencyMatrixMod);	// Done, free memory of intermediate structure
	return hyperVolume;
}