*** Settings ***
Library    SSHLibrary

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
${clone_id}    ${EMPTY}
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

BBS web interface should respond
    [Arguments]    ${host}
    ${rc} =    Execute Command    curl -kfsSL --resolve ${host}:443:127.0.0.1 https://${host}/
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

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
    # The web port allocated to the module is always taken
    ${web_port} =    Execute Command    runagent -m ${module_id} printenv TCP_PORT
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":${web_port},"admin_password":"${BBS_ADMIN_PASSWORD}"}'
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
    # The service restarts at the end of configure-module
    Wait Until Keyword Succeeds    60s    5s
    ...    BBS web interface should respond    bbs.example.test

Check if a clone does not start until it is configured
    ${output}  ${rc} =    Execute Command    api-cli run clone-module --data '{"module":"${module_id}","node":1,"replace":false}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${clone_id}    ${output.module_id}
    ${rc} =    Execute Command    runagent -m ${clone_id} systemctl --user is-active borgbackupserver.service
    ...    return_rc=True  return_stdout=False
    Should Not Be Equal As Integers    ${rc}  0
    ${output} =    Execute Command    api-cli run module/${clone_id}/get-configuration
    Should Contain    ${output}    "clone_pending": true

Check if a clone rejects the FQDN and SSH port of its source
    ${output}  ${rc} =    Execute Command    api-cli run module/${clone_id}/configure-module --data '{"fqdn":"bbs.example.test","lets_encrypt":false,"ssh_port":2223}'
    ...    return_rc=True
    Should Not Be Equal As Integers    ${rc}  0
    Should Contain    ${output}    fqdn_used_by_clone_source
    ${output}  ${rc} =    Execute Command    api-cli run module/${clone_id}/configure-module --data '{"fqdn":"bbs2.example.test","lets_encrypt":false,"ssh_port":2222}'
    ...    return_rc=True
    Should Not Be Equal As Integers    ${rc}  0
    Should Contain    ${output}    port_in_use

Check if a configured clone starts
    ${rc} =    Execute Command    api-cli run module/${clone_id}/configure-module --data '{"fqdn":"bbs2.example.test","lets_encrypt":false,"ssh_port":2223}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
    Wait Until Keyword Succeeds    60s    5s
    ...    BBS web interface should respond    bbs2.example.test
    ${output} =    Execute Command    api-cli run module/${clone_id}/get-configuration
    Should Contain    ${output}    "clone_pending": false

Check if the clone is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${clone_id}
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
