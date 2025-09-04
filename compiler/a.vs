@iterations = 10000

let a = 2

func test(b: scalar) -> scalar {
    let x = 10
    return b + x
}

func test1(b: scalar) -> scalar {
    let x = test(b)
    return x * 2
}

let c = test1(a)


@output = c