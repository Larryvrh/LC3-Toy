        .ORIG x3000
        LD R1,num1
        LD R2,num2
        AND R3,R3,#0
mul     ADD R3,R3,R1
        ADD R2,R2,#-1
        BRnp mul
        .END
num1    .FILL #5
num2    .FILL #4