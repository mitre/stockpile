param(
    [switch]$scan,
    [switch]$on,
    [switch]$off,
    [switch]$pref
)

if ($scan){
    Write-Host "Getting all WIFI networks"
    netsh wlan sh net mode=bssid
} elseif ($on) {
    Write-Host "Turning WIFI on"
} elseif ($off) {
    Write-Host "Turning WIFI off"
} elseif ($pref) {
    Write-Host "Getting preferred WIFI networks"
}
