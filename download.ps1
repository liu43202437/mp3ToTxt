# 简化版下载脚本 - 使用内置进度条
# 使用华为云镜像源下载Python
$url = "https://mirrors.huaweicloud.com/python/3.10.11/python-3.10.11-amd64.exe"
$output = "python-installer.exe"

# 避免中文乱码
$OutputEncoding = [System.Text.Encoding]::GetEncoding('gb2312')

Write-Output "[Info] Downloading Python installer from China mirror..."
Write-Output "[Info] Source: $url"
Write-Output "[Info] Target: $output"

try {
    $start_time = Get-Date
    
    # 使用Start-BitsTransfer下载并显示简单进度
    Import-Module BitsTransfer
    Start-BitsTransfer -Source $url -Destination $output -DisplayName "Python Installer" -Description "Downloading Python" -Priority High
    
    $end_time = Get-Date
    $time_taken = ($end_time - $start_time).TotalSeconds
    $fileSize = (Get-Item $output).Length / 1MB
    
    Write-Output "[Info] Download completed!"
    Write-Output "[Info] File size: $([Math]::Round($fileSize, 2)) MB"
    Write-Output "[Info] Time: $([Math]::Round($time_taken, 1)) seconds"
    Write-Output "[Info] Speed: $([Math]::Round($fileSize / $time_taken, 2)) MB/s"
    exit 0
}
catch {
    Write-Output "[Error] Download failed: $($_.Exception.Message)"
    Write-Output "[Info] Trying alternative mirror..."
    
    try {
        # 备用镜像 - 清华大学镜像
        $url = "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/archive/Miniconda3-py310_23.5.2-0-Windows-x86_64.exe"
        Write-Output "[Info] New source: $url"
        
        $start_time = Get-Date
        Start-BitsTransfer -Source $url -Destination $output -DisplayName "Python Installer (Alt)" -Description "Downloading Python" -Priority High
        
        $end_time = Get-Date
        $time_taken = ($end_time - $start_time).TotalSeconds
        $fileSize = (Get-Item $output).Length / 1MB
        
        Write-Output "[Info] Download from alternative mirror completed!"
        Write-Output "[Info] File size: $([Math]::Round($fileSize, 2)) MB"
        Write-Output "[Info] Time: $([Math]::Round($time_taken, 1)) seconds"
        exit 0
    }
    catch {
        Write-Output "[Error] All mirrors failed: $($_.Exception.Message)"
        exit 1
    }
} 