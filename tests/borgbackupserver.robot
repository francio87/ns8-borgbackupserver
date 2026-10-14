*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
# Characters that would break shell, env-file or SQL quoting
${BBS_ADMIN_PASSWORD}    Dfd90s%4&&%$&%$&àòàòà

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${ADMIN_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${ADMIN_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

*** Test Cases ***
Check if Borg Backup Server is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Take screenshots
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True
    Login to cluster-admin
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}
    Wait For Elements State    iframe >>> h2 >> text="Status"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/1._Status.png
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=settings
    Wait For Elements State    iframe >>> h2 >> text="Settings"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/2._Settings.png
    Close Browser

Check if the first configuration requires the admin password
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":2222}'
    ...    return_rc=True
    Should Not Be Equal As Integers    ${rc}  0
    Should Contain    ${output}    admin_password_required

Check if an occupied SSH port is rejected
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":443,"admin_password":"${BBS_ADMIN_PASSWORD}"}'
    ...    return_rc=True
    Should Not Be Equal As Integers    ${rc}  0
    Should Contain    ${output}    port_in_use

Check if Borg Backup Server can be configured
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":2222,"admin_password":"${BBS_ADMIN_PASSWORD}"}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the admin password is set without leaking it
    Put File    ${CURDIR}/check-admin-password.sh    /tmp/check-admin-password.sh    mode=0755
    ${rc} =    Execute Command    printf '%s' '${BBS_ADMIN_PASSWORD}' | /tmp/check-admin-password.sh ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    ${logs} =    Execute Command    runagent -m ${module_id} podman logs bbs    return_stderr=False
    Should Not Contain    ${logs}    ADMIN CREDENTIALS
    Should Not Contain    ${logs}    ${BBS_ADMIN_PASSWORD}
    ${inspect} =    Execute Command    runagent -m ${module_id} podman inspect bbs
    Should Not Contain    ${inspect}    ${BBS_ADMIN_PASSWORD}
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":2222,"admin_password":"${BBS_ADMIN_PASSWORD}"}'
    ...    return_rc=True
    Should Not Be Equal As Integers    ${rc}  0
    Should Contain    ${output}    admin_password_already_initialized

Check if the configuration can be saved without the admin password
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":2222}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the BBS web interface is reachable
    ${rc} =    Execute Command    curl -kfsSL --resolve bbs.example.test:443:127.0.0.1 https://bbs.example.test/
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if an update recreates the BBS container
    ${before} =    Execute Command    runagent -m ${module_id} podman inspect bbs --format '{{.Id}}'
    ${output}  ${rc} =    Execute Command    api-cli run update-module --data '{"module_url":"${IMAGE_URL}","instances":["${module_id}"],"force":true}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    ${after} =    Execute Command    runagent -m ${module_id} podman inspect bbs --format '{{.Id}}'
    Should Not Be Empty    ${before}
    Should Not Be Empty    ${after}
    Should Not Be Equal    ${before}    ${after}
    ${expected} =    Execute Command    runagent -m ${module_id} printenv BORGBACKUPSERVER_IMAGE
    ${actual} =    Execute Command    runagent -m ${module_id} podman inspect bbs --format '{{.ImageName}}'
    Should Be Equal    ${actual}    ${expected}

Check if Borg Backup Server is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the Borg SSH firewall service is removed
    ${rc} =    Execute Command    firewall-cmd --permanent --info-service=${module_id}
    ...    return_rc=True  return_stdout=False  return_stderr=False
    Should Not Be Equal As Integers    ${rc}  0
