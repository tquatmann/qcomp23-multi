import sys

if len(sys.argv) != 2:
    print("Usage:\npython {} <N>\n where <N> is the number of philosopher".format(sys.argv[0]))
N = int(sys.argv[1]);


model = r"""// randomized dining philosophers [LR81]
// dxp/gxn 23/01/02

// model which does not require fairness
// remove the possibility of loops:
// (1) cannot stay in thinking 
// (2) if first fork not free then cannot move (another philosopher must more)

mdp

// atomic formulae 
// left fork free and right fork free resp.
formula lfree = (p2>=0&p2<=4)|p2=6|p2=10;
formula rfree = (p%%N>=0&p3<=3)|p%%N=5|p%%N=7|p%%N=11;

module phil1

	p1: [0..11];

	[] p1=0 -> (p1'=1); // trying
	[] p1=1 -> 0.5 : (p1'=2) + 0.5 : (p1'=3); // draw randomly
	[] p1=2 &  lfree -> (p1'=4); // pick up left
	[] p1=3 &  rfree -> (p1'=5); // pick up right
	[] p1=4 &  rfree -> (p1'=8); // pick up right (got left)
	[] p1=4 & !rfree -> (p1'=6); // right not free (got left)
	[] p1=5 &  lfree -> (p1'=8); // pick up left (got right)
	[] p1=5 & !lfree -> (p1'=7); // left not free (got right)
	[] p1=6  -> (p1'=1); // put down left
	[] p1=7  -> (p1'=1); // put down right
	[] p1=8  -> (p1'=9); // move to eating (got forks)
	[] p1=9  -> (p1'=10); // finished eating and put down left 
	[] p1=9  -> (p1'=11); // finished eating and put down right
	[] p1=10 -> (p1'=0); // put down right and return to think
	[] p1=11 -> (p1'=0); // put down left and return to think

endmodule

// construct further modules through renaming
""".replace("%%N", str(N))

for i in range(2,N+1):
    l = i+1 if i+1<=N else 1
    r = i-1
    model += r"""module phil%%i = phil1 [ p1=p%%i, p2=p%%l, p3=p%%r ] endmodule""".replace("%%i", str(i)).replace("%%l",str(l)).replace("%%r", str(r)) + "\n"

model += r"""
// rewards (number of steps)
rewards "num_steps"
	[] true : 1;
endrewards

// labels
label "hungry" = """
model += "(" + "|".join([ "(p{}>0&p{}<8)".format(i,i) for i in range(1,N+1)]) + ");"
model += r"""
label "eat" = """
model += "(" + "|".join([ "(p{}>=8&p{}<=9)".format(i,i) for i in range(1,N+1)]) + ");"
model += r"""
rewards "think"
"""
for i in range(1,N+1):
    model += "\t(p{}=0) : 1;\n".format(i)
model += r"""
endrewards

rewards "eat"
"""
for i in range(1,N+1):
    model += "\t(p{}>=8)&(p{}<=9) : 1;\n".format(i,i)
model += r"""
endrewards

"""
for i in range(1,N+1):
    model += "rewards \"eat{}\"\n\t(p{}>=8)&(p{}<=9) : 1;\nendrewards\n\n".format(i,i,i)

print(model)