

def two(pos, first, second):
	print("module n{pos}=n11[s11=s{pos},detect11=detect{pos},attack21_11=attack{first}_{pos},attack12_11=attack{second}_{pos},attack11_21=attack{pos}_{first},attack11_12=attack{pos}_{second},clean_11=clean_{pos}] endmodule".format(pos=pos,first=first,second=second))
    
def three(pos, first, second, third):
    print("module n{pos}=n21[s21=s{pos},detect21=detect{pos},attack31_21=attack{first}_{pos},attack22_21=attack{second}_{pos},attack11_21=attack{third}_{pos},attack21_31=attack{pos}_{first},attack21_22=attack{pos}_{second},attack21_11=attack{pos}_{third},clean_21=clean_{pos}] endmodule".format(pos=pos,first=first,second=second,third=third))

def four(pos, first, second, third, fourth):
    print("module n{pos}=n22[s22=s{pos},detect22=detect{pos},attack32_22=attack{first}_{pos},attack23_22=attack{second}_{pos},attack12_22=attack{third}_{pos},attack21_22=attack{fourth}_{pos},attack22_32=attack{pos}_{first},attack22_23=attack{pos}_{second},attack22_12=attack{pos}_{third},attack22_21=attack{pos}_{fourth},clean_22=clean_{pos}] endmodule".format(pos=pos,first=first,second=second,third=third,fourth=fourth))


# module copying for virus4

print("// first column")
three("31", "41", "32", "21")
two("41", "42", "31")

print("// second column")
three("12", "22", "13", "11")
print("// n22")
four("32", "42", "33", "22", "31")
three("42", "43", "32", "41")

print("// third column")
three("13", "23", "14", "12")
four("23", "33", "24", "13", "22")
four("33", "43", "34", "23", "32")
three("43", "44", "33", "42")

print("// fourth column")
two("14", "24", "13")
three("24", "34", "14", "23")
three("34", "44", "24", "33")
two("44", "34", "43")
