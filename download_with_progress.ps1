# 下载脚本，带进度显示
$url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
$output = "python-installer.exe"

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$wc = New-Object System.Net.WebClient

# 获取文件大小
try {
    $request = [System.Net.HttpWebRequest]::Create($url)
    $request.Method = "HEAD"
    $response = $request.GetResponse()
    $totalBytes = $response.ContentLength
    $totalMB = [Math]::Round($totalBytes / 1MB, 2)
    $response.Close()
    
    Write-Host "[信息] 文件大小: $totalMB MB"
} catch {
    Write-Host "[警告] 无法获取文件大小: $_"
    $totalBytes = 0
}

# 创建临时文件
$tempFile = [System.IO.Path]::GetTempFileName()
$writer = New-Object System.IO.FileStream $tempFile, ([System.IO.FileMode]::Create)

# 下载状态变量
$downloadedBytes = 0
$lastPercentage = 0
$lastSpeedCheck = 0
$bytesFromLastSpeedCheck = 0
$lastSpeedUpdate = $stopwatch.ElapsedMilliseconds

# 下载缓冲区
$bufferSize = 1MB
$buffer = New-Object byte[] $bufferSize

# 下载过程显示函数
function Show-Progress {
    param (
        [long]$downloaded,
        [long]$total
    )
    
    if ($total -gt 0) {
        $percentage = [Math]::Round(($downloaded / $total) * 100, 0)
        
        # 计算下载速度
        $currentTime = $stopwatch.ElapsedMilliseconds
        $timeSpan = ($currentTime - $lastSpeedUpdate) / 1000
        
        if ($timeSpan -ge 1) { # 至少1秒更新一次速度
            $bytesChange = $downloaded - $bytesFromLastSpeedCheck
            $speed = [Math]::Round(($bytesChange / $timeSpan) / 1KB, 2)
            
            $script:bytesFromLastSpeedCheck = $downloaded
            $script:lastSpeedUpdate = $currentTime
            
            $downloadedMB = [Math]::Round($downloaded / 1MB, 2)
            $totalMB = [Math]::Round($total / 1MB, 2)
            
            # 更新进度条 - 每5%更新一次
            if ($percentage -ge ($script:lastPercentage + 5) -or $percentage -eq 100) {
                $script:lastPercentage = $percentage
                $progressBar = "[" + ("=" * [Math]::Floor($percentage / 5)) + ">" + (" " * [Math]::Ceiling((100 - $percentage) / 5)) + "]"
                Write-Host "`r[进度] $progressBar $percentage% ($downloadedMB MB / $totalMB MB) 速度: $speed KB/s   " -NoNewline
            }
        }
    }
}

try {
    # 打开请求
    $request = [System.Net.HttpWebRequest]::Create($url)
    $response = $request.GetResponse()
    $responseStream = $response.GetResponseStream()
    
    # 下载循环
    do {
        # 读取一块数据
        $bytesRead = $responseStream.Read($buffer, 0, $buffer.Length)
        if ($bytesRead -gt 0) {
            # 写入临时文件
            $writer.Write($buffer, 0, $bytesRead)
            $downloadedBytes += $bytesRead
            
            # 显示进度
            Show-Progress -downloaded $downloadedBytes -total $totalBytes
        }
    } while ($bytesRead -gt 0)
    
    # 完成
    Write-Host "`r[完成] 下载完成! 100% ($([Math]::Round($downloadedBytes / 1MB, 2)) MB) 总用时: $([Math]::Round($stopwatch.Elapsed.TotalSeconds, 1)) 秒     "
    
    # 关闭流
    $responseStream.Close()
    $response.Close()
    $writer.Close()
    
    # 移动到目标文件
    Move-Item -Path $tempFile -Destination $output -Force
    
    # 验证文件
    if (Test-Path $output) {
        $fileSize = (Get-Item $output).Length
        if ($fileSize -gt 0) {
            Write-Host "[信息] 文件已保存: $output (大小: $([Math]::Round($fileSize / 1MB, 2)) MB)"
            exit 0
        } else {
            Write-Host "[错误] 下载的文件大小为0"
            exit 1
        }
    } else {
        Write-Host "[错误] 下载后无法找到文件"
        exit 1
    }
} catch {
    Write-Host "`n[错误] 下载失败: $($_.Exception.Message)"
    exit 1
} finally {
    if ($null -ne $responseStream) { $responseStream.Close() }
    if ($null -ne $response) { $response.Close() }
    if ($null -ne $writer) { $writer.Close() }
    if ((Test-Path $tempFile) -and ($tempFile -ne $output)) {
        Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
    }
} 