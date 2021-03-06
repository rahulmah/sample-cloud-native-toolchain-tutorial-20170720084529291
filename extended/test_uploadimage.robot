*** Settings ***
Documentation         Test upload image with both valid and invalid images.
...                   This test expects there to be bad image tarballs named
...                   pnor_bad_manifest.tar and pnor_no_image.tar on the TFTP
...                   server and in the directory BAD_IMAGES_DIR_PATH.
...                   Execution Method :
...                   python -m robot -v OPENBMC_HOST:<hostname>
...                   -v TFTP_SERVER:<TFTP server IP>
...                   -v TFTP_FILE_NAME:<filename.tar>
...                   -v IMAGE_FILE_PATH:<path/*.tar> test_uploadimage.robot
...                   -v BAD_IMAGES_DIR_PATH:<path>

Resource              ../lib/connection_client.robot
Resource              ../lib/rest_client.robot
Resource              ../lib/openbmc_ffdc.robot
Library               Collections
Library               String
Library               OperatingSystem
Library               test_uploadimage.py

Test Teardown  Upload Image Teardown

Force Tags  Upload_Test

*** Variables ***
${timeout}            10
${upload_dir_path}    /tmp/images/
${QUIET}              ${1}
${image_version}      ${EMPTY}

*** Test Cases ***

Upload Image Via REST
    [Documentation]  Upload an image via REST.
    [Tags]  Upload_Image_Via_REST

    OperatingSystem.File Should Exist  ${IMAGE_FILE_PATH}
    ${IMAGE_VERSION}=  Get Version Tar  ${IMAGE_FILE_PATH}
    ${image_data}=  OperatingSystem.Get Binary File  ${IMAGE_FILE_PATH}
    Upload Image To BMC  /upload/image  data=${image_data}
    ${ret}=  Verify Image Upload
    Should Be True  True == ${ret}

Upload Image Via TFTP
    [Documentation]  Upload an image via TFTP.
    [Tags]  Upload_Image_Via_TFTP

    @{image}=  Create List  ${TFTP_FILE_NAME}  ${TFTP_SERVER}
    ${data}=  Create Dictionary  data=@{image}
    ${resp}=  OpenBMC Post Request
    ...  ${SOFTWARE_VERSION}/action/DownloadViaTFTP  data=${data}
    Should Be Equal As Strings  ${resp.status_code}  ${HTTP_OK}
    Sleep  1 minute
    ${upload_file}=  Get Latest File  ${upload_dir_path}
    ${image_version}=  Get Image Version
    ...  ${upload_dir_path}${upload_file}/MANIFEST
    ${ret}=  Verify Image Upload
    Should Be True  True == ${ret}

Upload Image With Bad Manifest Via REST
    [Documentation]  Upload an image with a MANIFEST with an invalid
    ...              purpose via REST and make sure the BMC does not unpack it.
    [Tags]  Upload_Image_With_Bad_Manifest_Via_REST

    ${bad_image_file_path}=  OperatingSystem.Join Path  ${BAD_IMAGES_DIR_PATH}
    ...  pnor_bad_manifest.tar
    OperatingSystem.File Should Exist  ${bad_image_file_path}
    ...  msg=Invalid PNOR image pnor_bad_manifest.tar not found
    ${bad_image_version}=  Get Version Tar  ${bad_image_file_path}
    ${bad_image_data}=  OperatingSystem.Get Binary File  ${bad_image_file_path}
    Upload Post Request  /upload/image  data=${bad_image_data}
    Verify Image Not In BMC Uploads Dir  ${bad_image_version}

Upload Image With Bad Manifest Via TFTP
    [Documentation]  Upload an image with a MANIFEST with an invalid
    ...              purpose via TFTP and make sure the BMC does not unpack it.
    [Tags]  Upload_Image_With_Bad_Manifest_Via_TFTP

    @{image}=  Create List  pnor_bad_manifest.tar  ${TFTP_SERVER}
    ${data}=  Create Dictionary  data=@{image}
    ${resp}=  OpenBMC Post Request
    ...  ${SOFTWARE_VERSION_URI}/action/DownloadViaTFTP  data=${data}
    Should Be Equal As Strings  ${resp.status_code}  ${HTTP_OK}
    ${bad_image_version}=  Get Image Version From TFTP Server
    ...  pnor_bad_manifest.tar
    Verify Image Not In BMC Uploads Dir  ${bad_image_version}

Upload Image With No Squashfs Via REST
    [Documentation]  Upload an image with no pnor.xz.suashfs file via REST and
    ...              make sure the BMC does not unpack it.
    [Tags]  Upload_Image_With_No_Squashfs_Via_REST

    ${bad_image_file_path}=  OperatingSystem.Join Path  ${BAD_IMAGES_DIR_PATH}
    ...  pnor_no_image.tar
    OperatingSystem.File Should Exist  ${bad_image_file_path}
    ...  msg=Invalid PNOR image pnor_no_image.tar not found
    ${bad_image_version}=  Get Version Tar  ${bad_image_file_path}
    ${bad_image_data}=  OperatingSystem.Get Binary File  ${bad_image_file_path}
    Upload Post Request  /upload/image  data=${bad_image_data}
    Verify Image Not In BMC Uploads Dir  ${bad_image_version}

Upload Image With No Squashfs Via TFTP
    [Documentation]  Upload an image with no pnor.xz.suashfs file via TFTP and
    ...              make sure the BMC does not unpack it.
    [Tags]  Upload_Image_With_No_Squashfs_Via_TFTP

    @{image}=  Create List  pnor_no_image.tar  ${TFTP_SERVER}
    ${data}=  Create Dictionary  data=@{image}
    ${resp}=  OpenBMC Post Request
    ...  ${SOFTWARE_VERSION_URI}/action/DownloadViaTFTP  data=${data}
    Should Be Equal As Strings  ${resp.status_code}  ${HTTP_OK}
    ${bad_image_version}=  Get Image Version From TFTP Server
    ...  pnor_no_image.tar
    Verify Image Not In BMC Uploads Dir  ${bad_image_version}

*** Keywords ***

Upload Image Teardown
    [Documentation]  Log FFDC if test fails for debugging purposes.

    Open Connection And Log In
    Execute Command On BMC  rm -rf /tmp/images/*

    Close All Connections
    FFDC On Test Case Fail


Upload Post Request
    [Arguments]  ${uri}  ${timeout}=10  ${quiet}=${QUIET}  &{kwargs}

    # Description of argument(s):
    # uri             URI for uploading image via REST.
    # timeout         Time allocated for the REST command to return status.
    # quiet           If enabled turns off logging to console.
    # kwargs          A dictionary that maps each keyword to a value.

    Initialize OpenBMC  ${timeout}  quiet=${quiet}
    ${base_uri}=  Catenate  SEPARATOR=  ${DBUS_PREFIX}  ${uri}
    ${headers}=  Create Dictionary  Content-Type=application/octet-stream
    ...  Accept=application/octet-stream
    Set To Dictionary  ${kwargs}  headers  ${headers}
    Run Keyword If  '${quiet}' == '${0}'  Log Request  method=Post
    ...  base_uri=${base_uri}  args=&{kwargs}
    ${ret}=  Post Request  openbmc  ${base_uri}  &{kwargs}  timeout=${timeout}
    Run Keyword If  '${quiet}' == '${0}'  Log Response  ${ret}
    Should Be Equal As Strings  ${ret.status_code}  ${HTTP_OK}


Get Image Version From TFTP Server
    [Documentation]  Get the version dfound in the MANIFEST file of
    ...              an image on the given TFTP server.
    [Arguments]  ${image_file_path}

    # Description of argument(s):
    # image_file_path  The path to the image on the TFTP server,
    #                  ommitting a leading /.

    ${rc}=  OperatingSystem.Run And Return RC
    ...  curl -s tftp://${TFTP_SERVER}/${image_file_path} > bad_image.tar
    Should Be Equal As Integers  0  ${rc}
    ...  msg=Could not download image to check version.
    ${version}=  Get Version Tar  bad_image.tar
    OperatingSystem.Remove File  bad_image.tar
    [Return]  ${version}
