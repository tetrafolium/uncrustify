/**
 * @file align_add.h
 *
 * @author  Guy Maurel
 * split from align.cpp
 * @author  Ben Gardner
 * @license GPL v2+
 */

#ifndef ALIGN_ADD_H_INCLUDED
#define ALIGN_ADD_H_INCLUDED

#include "ChunkStack.h"
#include "chunk_list.h"

void align_add(ChunkStack &cs, chunk_t *pc, size_t &max_col);

#endif /* ALIGN_ADD_H_INCLUDED */
