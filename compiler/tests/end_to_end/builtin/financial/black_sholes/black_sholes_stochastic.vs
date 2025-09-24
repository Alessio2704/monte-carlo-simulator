@iterations = 1
@output = z

let random_spot = Normal(100, 10)
let z = BlackScholes(random_spot, 110, 0.05, 0.5, 0.2, "call")