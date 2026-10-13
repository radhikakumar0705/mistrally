# Algorithms

## Big-O notation

Big-O describes how running time grows with input size. Binary search on a sorted array runs in O(log n) because each comparison halves the remaining range, while scanning an unsorted array is O(n).

## Hash tables

A hash table maps keys to buckets with a hash function. When two keys land in the same bucket it is a collision, resolved by chaining entries in a list or by open addressing, which probes for the next free slot.

## Sorting

Merge sort is stable and always runs in O(n log n) time but needs O(n) extra memory. Quicksort sorts in place and is fast on average, but its worst case is O(n^2) when the pivot choices are consistently bad.

## Recursion

A recursive function calls itself on a smaller version of the problem. Every recursive function needs a base case that stops the recursion; without one, Python raises RecursionError after about 1000 nested calls.

## Graph traversal

Breadth-first search explores neighbours level by level using a queue and finds shortest paths in unweighted graphs. Depth-first search follows one branch as far as possible using a stack or recursion.

## Dynamic programming

Dynamic programming solves problems with overlapping subproblems by storing results. Memoization caches the result of each call, which turns the exponential naive Fibonacci into a linear-time algorithm.
