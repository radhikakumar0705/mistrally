# SQL guide

## Inner join

An inner join returns only the rows that have matching values in both tables. Rows without a partner on the other side are dropped from the result.

## Left join

A left join keeps every row from the left table. When the right table has no matching row, its columns are filled with NULL, which is how you find customers who have never placed an order.

## Indexes

An index is usually a B-tree that lets the database find rows without scanning the whole table. Indexes speed up reads and filters but slow down inserts and updates, because each index must be maintained on every write.

## Grouping

GROUP BY collapses rows that share values into one row per group so you can aggregate them with COUNT, SUM or AVG. Filter groups after aggregation with HAVING; WHERE filters individual rows before grouping.

## Transactions

A transaction groups statements so they succeed or fail together. ACID stands for atomicity, consistency, isolation and durability. If something goes wrong midway, ROLLBACK undoes every change made since the transaction began.

## The N+1 query problem

The N+1 problem happens when code runs one query to load a list and then one more query per item to load related data. Fix it with a join or by eager loading the related rows in a single extra query.
