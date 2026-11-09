# Coordinator calibration checks

These three sampled claims were checked by the coordinator, independently of the batch checkers and before seeing their results. Comparing the verdicts tests how reliable the checkers are.

| id | verdict | evidence |
|---|---|---|
| 01-47 | CORRECT | `fwmap.py tasks`: CPU1 task 0x1001, entry 0x7E42691F, pri 1, attr 2 (TA_ACT). |
| 04-105 | CORRECT | MOVART_TASK entry 0x7E6CBEBC calls 0x7E6DABAF (`[MOV]img_exec :`), 0x7E6DB6D1 (`[MOV_KDG] mov_kdg_exec() in`), plus the queue read/write helpers 0x7E6DD826/0x7E6DD86E. |
| 08-59 | MINOR | The 53-byte USB 2.0 TEST_PACKET starts at **0x7F0D7C58**: nine 0x00 bytes, then the AA, EE, FE/FF and 7F BF DF… runs. The claim gives 0x7F0D7C61, which is where the AA run begins, 9 bytes in. The last byte reads 0xE7 where the published pattern has 0x7E (not checked further). |
