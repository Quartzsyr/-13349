; -- Inno Setup Script for Solar Rover Serial Assistant --
; 植护小车串口控制程序安装脚本
; 嵌入式系统设计竞赛作品 - 队伍编号：13349
; 开发者：石殷睿
; 版本：V1.2
; 
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "植护小车串口控制程序"
#define MyAppVersion "1.2"
#define MyAppPublisher "石殷睿"
#define MyAppURL "https://www.quartz.xin/"
#define MyAppExeName "serial_assistant.exe"
#define MyOutputBaseFilename "嵌入式大赛13349自制串口控制程序"
#define MyTeamNumber "13349"
#define MyCompetition "全国大学生嵌入式系统设计竞赛"
#define MyAppDescription "基于太阳能的智能植护小车串口控制程序"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{C1A6E7B8-4B8C-4B1D-9B7C-8E2A7D2C0F4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} V{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2024 {#MyAppPublisher}
AppComments={#MyAppDescription} - {#MyCompetition}队伍编号{#MyTeamNumber}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputBaseFilename={#MyOutputBaseFilename}
OutputDir=Output
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 设置安装程序图标
SetupIconFile=icon.ico
; 卸载程序图标
UninstallDisplayIcon={app}\{#MyAppExeName}
; 安装前信息文件
InfoBeforeFile=info_before_install.txt
; 安装后信息文件
InfoAfterFile=info_after_install.txt
; 许可协议文件
LicenseFile=license.txt
; 最小Windows版本
MinVersion=6.1sp1
; 架构支持
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; 特权级别
PrivilegesRequired=lowest
; 关闭旧版本检查
DisableWelcomePage=no
; 安装程序标题
AppendDefaultDirName=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
; 主程序文件
Source: "{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 应用程序图标
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify
Name: "{app}\temp"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.txt"; Comment: "查看使用说明"
Name: "{group}\队伍信息"; Filename: "{app}\team_info.txt"; Comment: "查看竞赛队伍信息"
Name: "{group}\访问官网"; Filename: "{#MyAppURL}"; Comment: "访问开发者网站"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; 安装Visual C++ 运行时（如果需要）
Filename: "{tmp}\vcredist_x64.exe"; Parameters: "/quiet"; StatusMsg: "正在安装运行时库..."; Flags: runhidden skipifdoesntexist
; 启动主程序
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载前清理
Filename: "{app}\{#MyAppExeName}"; Parameters: "/cleanup"; RunOnceId: "CleanupApp"; Flags: runhidden skipifdoesntexist

[Code]
// 安装前检查
function InitializeSetup(): Boolean;
begin
  Result := True;
  if MsgBox('欢迎安装植护小车串口控制程序！' + #13#10 + #13#10 + 
            '竞赛信息：' + #13#10 +
            '• 全国大学生嵌入式系统设计竞赛' + #13#10 +
            '• 队伍编号：13349' + #13#10 +
            '• 开发者：石殷睿' + #13#10 + #13#10 +
            '确定要继续安装吗？', 
            mbConfirmation, MB_YESNO) = IDNO then
    Result := False;
end;

// 安装完成后的处理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 创建队伍信息文件
    SaveStringToFile(ExpandConstant('{app}\team_info.txt'), 
      '=== 竞赛队伍信息 ===' + #13#10 +
      '竞赛名称：全国大学生嵌入式系统设计竞赛' + #13#10 +
      '队伍编号：13349' + #13#10 +
      '项目名称：基于太阳能的智能植护小车' + #13#10 +
      '开发者：石殷睿' + #13#10 +
      '版本：V1.2' + #13#10 +
      '开发时间：2024年' + #13#10 +
      '联系方式：' + ExpandConstant('{#MyAppURL}') + #13#10 +
      '软件描述：串口控制程序，用于控制植护小车的各项功能' + #13#10 +
      '=== 使用说明 ===' + #13#10 +
      '1. 连接植护小车的串口设备' + #13#10 +
      '2. 启动程序并选择正确的串口' + #13#10 +
      '3. 根据界面提示操作小车' + #13#10 +
      '4. 如遇问题请参考使用手册或联系开发者' + #13#10, 
      False);
  end;
end;

// 安装完成提示
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption := 
      '植护小车串口控制程序安装完成！' + #13#10 + #13#10 +
      '感谢您使用我们的竞赛作品！' + #13#10 +
      '队伍编号：13349' + #13#10 +
      '如有任何问题或建议，请访问：' + ExpandConstant('{#MyAppURL}');
  end;
end;

// 卸载前确认
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if MsgBox('确定要卸载植护小车串口控制程序吗？' + #13#10 + #13#10 +
            '卸载后将删除所有程序文件，但会保留用户配置。', 
            mbConfirmation, MB_YESNO) = IDNO then
    Result := False;
end;

// 卸载完成提示
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgBox('植护小车串口控制程序已成功卸载！' + #13#10 + #13#10 +
           '感谢您的使用！如有需要，欢迎重新安装。' + #13#10 +
           '队伍编号：13349 | 开发者：石殷睿', 
           mbInformation, MB_OK);
  end;
end;