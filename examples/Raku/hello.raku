my $total = 0;

for 1 .. 5 -> $n {
    $total += $n;
}

say "total=$total";
