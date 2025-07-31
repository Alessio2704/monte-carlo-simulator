@iterations = 1000000

let a = 1

let b = Normal(1, 0.01)

let cc = 1 + (1 - 4)^2 + 2*1 - (npv(Pert(0.04, 0.05, 0.06), [1,2,3,4]))

@output = cc
@output_file = "results.csv"