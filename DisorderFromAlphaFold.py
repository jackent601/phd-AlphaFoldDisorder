import numpy as np
from Bio.PDB import PDBParser
# ================================================================================================================================
#   DISORDER (pLDDT) Fractions
# ================================================================================================================================

def getpLDDTsFromAlphaFoldPDBModel(pdb_model):
    """
    AlphaFold stores plDDT as B-factor, pLDDT calculated per residue to only need to query first atom, returns array of pLDDT values (per residue)
    """
    return np.array([next(r.get_atoms()).get_bfactor() for r in pdb_model.get_residues()])

def getpLDDTsSubSequenceFromAlphaFoldPDBModel(pdb_model, startRes=None, endRes=None):
    """
    Returns pLDDTs of a sub-sequence within AF model, note: python is zero indexed, residue numbers are not!
    """
    if endRes is None and startRes is None:
        # read whole sequence
        return getpLDDTsFromAlphaFoldPDBModel(pdb_model)
    else:
        # filter for subsequence
        # Check both bounds provided
        assert startRes is not None and endRes is not None, "Must provide BOTH of start res and end res if specified"
        # SubSequencing Checks
        assert startRes <= endRes, "Start Residue number sub-sequence is greater than end residue number!"
        # Check Residue length is not larger than AlphaFold sequence
        _AFSequenceLength = len(list(pdb_model.get_residues()))
        assert endRes - startRes <= _AFSequenceLength, "Residue Sub Selection larger than AlphaFold sequence!"
        # Check bounds within AlphaFold Sequence
        assert endRes <= _AFSequenceLength, "Residue Sub Selection outside of AlphaFold Sequence!"

        return getpLDDTsFromAlphaFoldPDBModel(pdb_model)[startRes-1:endRes]

def getConsecutivepLDDTFromThreshold(pLDDTs, pLDDTThreshold, aboveThreshold=False):
    """
    finds the length of all stretches of residues consecutively below (or above if flag set) a pLDDT threshold i.e. 'disordered' (or 'ordered') stretches
    returns both the list of indices where each stretch starts, and the length of each stretch
    pLDDTs should be an array of pLDDTs from AF PDB file
    """
    # Finds indices in pLDDT list that are below threshold
    if aboveThreshold:
        pLDDTIndices = np.argwhere(pLDDTs >= pLDDTThreshold)[:, 0]
    else:
        pLDDTIndices = np.argwhere(pLDDTs <= pLDDTThreshold)[:, 0]
    
    # Catch Case of No Disorder (within threshold)
    if len(pLDDTIndices) == 0:
        return None, None
    
    # Need to duplicate final index value for calculating the lengths below in while loop 
    pLDDTIndices = np.append(pLDDTIndices, pLDDTIndices[-1])

    # Find where difference between adjacent indices is greater than 1 
    # (This indicates the begining of a new stretch of consecutively low pLDDTs regions)
    # (Adds one to correct for shifting array)
    consecutivepLDDTIndices = np.where(pLDDTIndices[1:] - pLDDTIndices[:-1] > 1)[0] + 1

    # Prepends with zero to account for first length
    consecutivepLDDTIndices = np.insert(consecutivepLDDTIndices, 0, 0)

    # Calculate length of each consecutively low pLDDT sequence
    consecutiveLens = np.zeros(len(consecutivepLDDTIndices)).astype(np.int64)
    for i in range(len(consecutivepLDDTIndices)):
        _length = 1
        _idx = consecutivepLDDTIndices[i]
        while pLDDTIndices[_idx+1] == pLDDTIndices[_idx] + 1:
            _length += 1
            _idx += 1
        consecutiveLens[i] = _length
    return consecutivepLDDTIndices, consecutiveLens
    
def getConsecutiveDisorderedFrompLDDTs(pLDDTs, pLDDTDisorderThreshold):
    """
    getConsecutivepLDDTFromThreshold with above flag set to false
    """
    return getConsecutivepLDDTFromThreshold(pLDDTs, pLDDTDisorderThreshold, aboveThreshold=False)

def getConsecutiveOrderedFrompLDDTs(pLDDTs, pLDDTOrderThreshold):
    """
    getConsecutivepLDDTFromThreshold with above flag set to True
    """
    return getConsecutivepLDDTFromThreshold(pLDDTs, pLDDTOrderThreshold, aboveThreshold=True)

def getDisorderedFractionFrompLDDTs(pLDDTs, pLDDTDisorderThreshold, numberConsectuivelyDisorderThreshold):
    """
    Uses getConsecutiveDisorderLengthsFrompLDDTs to get length of all stretches of residues consecutively below a pLDDT threshold (i.e. 'disordered' stretches) 
    Then filters lengths for those above or equal to length threshold
    Returns the disordered 'fraction', along with raw lengths of disordered residues within stretches above threshold
    """
    disorderedStretchesIndices, disorderedStretchesLengths = getConsecutiveDisorderedFrompLDDTs(pLDDTs, pLDDTDisorderThreshold)

    if disorderedStretchesIndices is None or disorderedStretchesLengths is None:
        return 0, None
    
    disorderedLengthsFiltered = disorderedStretchesLengths[disorderedStretchesLengths >= numberConsectuivelyDisorderThreshold]
    
    return sum(disorderedLengthsFiltered)/len(pLDDTs), disorderedLengthsFiltered

# ================================================================================================================================
#   Functions From PDB Paths
# ================================================================================================================================

def getDisorderedFractionFromPDB(PDBpath, pLDDTDisorderThreshold, numberConsectuivelyDisorderThreshold, startRes=None, endRes=None):
    """
    getDisorderedFractionFrompLDDTs but reads directly from a PDB path, including option to sub sequence
    """
    # Read PDB
    parser = PDBParser()
    structure = parser.get_structure('auto_read', PDBpath)

    # Get Model, AlphaFold PDBs only have 1
    pdb_model = structure[0]

    # Get pLDDTs
    pLDDTs = getpLDDTsSubSequenceFromAlphaFoldPDBModel(pdb_model, startRes=startRes, endRes=endRes)

    # Get 'disordered' fractions
    return getDisorderedFractionFrompLDDTs(pLDDTs, pLDDTDisorderThreshold, numberConsectuivelyDisorderThreshold)
