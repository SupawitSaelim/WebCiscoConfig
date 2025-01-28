#define MyAppName "NetworkAutomation"
#define MyAppVersion "1.0"
#define MyAppPublisher "SupawitSaelim"
#define MyAppExeName "NetworkAutomation.exe"

[Setup]
AppId={{com.supawitsaelim.networkautomation}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright © 2025 SupawitSaelim
AppComments=Network Automation Tool for Network Management
AppContact=supawit.sae@ku.th
AppSupportURL=https://github.com/SupawitSaelim
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=NetworkAutomation_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main application files
Source: "C:\Users\oatsu\OneDrive\Desktop\NetAutomation\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Flags: createonlyiffileexists

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  MongoURIPage: TInputQueryWizardPage;
  
// Function to check if Node.js is installed
function IsNodeJSInstalled: Boolean;
var
  ErrorCode: Integer;
begin
  Result := False;
  if ShellExec('', 'node', '--version', '', SW_HIDE, False, ErrorCode) then
  begin
    Result := True;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = wpWelcome then
  begin
    // Check for Node.js installation
    if not IsNodeJSInstalled then
    begin
      MsgBox('Node.js is required for this application but was not found.' + #13#10 +
             'Please install Node.js before continuing.' + #13#10 +
             'You can download it from: https://nodejs.org', 
             mbCriticalError, MB_OK);
      Result := False;
      WizardForm.Close;
      Exit;
    end;
  end;

  if CurPageID = MongoURIPage.ID then
  begin
    // Check if MongoDB URI is empty
    if MongoURIPage.Values[0] = '' then
    begin
      if MsgBox('MongoDB URI is required. Do you want to cancel the installation?', 
         mbConfirmation, MB_YESNO) = IDYES then
      begin
        Result := False;
        WizardForm.Close;
      end;
    end;
  end;
end;

procedure InitializeWizard;
begin
  // Create MongoDB URI input page
  MongoURIPage := CreateInputQueryPage(wpWelcome,
    'Database Configuration', 
    'Please enter your MongoDB connection details',
    'This information will be saved in your .env file');
  
  // Add MongoDB URI input field with example
  MongoURIPage.Add('MongoDB URI:', False);
  MongoURIPage.SubCaptionLabel.Caption := 'Example: mongodb+srv://username:password@cluster.mongodb.net/' + #13#10 +
    'Sample: mongodb+srv://supawit:Supawitadmin123_@devices.ipclc.mongodb.net/';
end;

procedure CreateEnvFile();
var
  EnvFile: String;
begin
  // Create .env file in installation directory
  EnvFile := ExpandConstant('{app}\.env');
  SaveStringToFile(EnvFile, 
    'MONGO_URI=' + MongoURIPage.Values[0] + #13#10, 
    False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    CreateEnvFile();
end;