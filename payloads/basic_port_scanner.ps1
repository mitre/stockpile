function PrefixLength-ToAddrInt {
    param ([Parameter(Mandatory=$true)][int]$prefixLength);
    ([Math]::Pow(2, $prefixLength) - 1) * [Math]::Pow(2, 32 - $prefixLength);
};
function IPv4-ToInt {
    param ([Parameter(Mandatory=$true)][string]$ipv4);
    $octets = $ipv4 -split "\." | %{ [int]$_ };
    ($octets[0]*[Math]::Pow(256,3)) + ($octets[1]*[Math]::Pow(256,2)) + ($octets[2]*256) + $octets[3];
};
function Int-ToIPv4 {
    param ([Parameter(Mandatory=$true)][uint32]$ipv4int);
    $octets = @();
    $remainder = $ipv4int;
    3..0 | %{
        $divideBy = [Math]::Pow(256, $_);
        $octet = [int]($remainder / $divideBy);
        $octets += [string]$octet;
        $remainder = $remainder % $divideBy;
    };
    $octets -join '.';
};
function Get-NetAddrInt {
    param (
        [Parameter(Mandatory=$true)][string]$ipv4,
        [Parameter(Mandatory=$true)][int]$prefixLength
    );
    $maskInt = PrefixLength-ToAddrInt $prefixLength;
    $ipv4int = IPv4-ToInt $ipv4;
    $maskInt -band $ipv4Int;
};
function Scan-Netrange {
    param (
        [Parameter(Mandatory=$true)][string]$ipv4,
        [Parameter(Mandatory=$true)][int]$prefixLength,
        [Parameter(Mandatory=$true)][[]int]$ports
    );
    $netAddrInt = Get-NetAddrInt -ipv4 $ipv4 -prefixLength $prefixLength;
    $startAddrInt = $netAddrInt + 1;
    $endAddrInt = $netAddrInt + [Math]::Pow(2, 32 - $prefixLength) - 1;
    $startAddrInt..$endAddrInt | %{
        $ipv4 = Int-ToIpv4 $_;
        Write-Host "------";
        Write-Host $ipv4;
        $ports | %{
            $socket = new-object system.net.sockets.tcpclient;
            $Connection = $socket.beginconnect($ipv4, $_, $null, $null);
            $Connection.AsyncWaitHandle.waitOne(50,$false) | out-null;
            if ($socket.connected -eq $true) { echo "Port $_ is open!"};
            $socket.Close | Out-Null;
        };
    };
};
